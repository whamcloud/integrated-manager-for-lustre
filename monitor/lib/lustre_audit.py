#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.core.management import setup_environ
import settings
setup_environ(settings)

# Access to 'monitor' database
from monitor.models import *
from django.db import transaction

import re
import sys
import traceback
import simplejson as json

import logging
audit_log = logging.getLogger('audit')
audit_log.setLevel(logging.DEBUG)
handler = logging.FileHandler(settings.AUDIT_LOG_PATH)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
audit_log.addHandler(handler)
if settings.DEBUG:
    audit_log.setLevel(logging.DEBUG)
    audit_log.addHandler(logging.StreamHandler())
else:
    audit_log.setLevel(logging.INFO)


def normalize_nid(string):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow 
       direct comparisons between NIDs"""
    if string[-4:] == "@tcp":
        return string + "0"
    else:
        return string

def normalize_nids(nid_list):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow 
       direct comparisons between NIDs"""
    return [normalize_nid(n) for n in nid_list]

class NoLNetInfo(Exception):
    pass

class LustreAudit:
    def __init__(self):
        self.raw_data = None
        self.target_locations = None
        self.audited_mountables = {}
    
    def is_primary(self, local_target_info):
        local_nids = set([n.nid_string for n in self.host.nid_set.all()])

        if not local_target_info['params'].has_key('failover.node'):
             # If the target has no failover nodes, then it is accessed by only 
             # one (primary) host, i.e. this one
             primary = True
        elif len(local_nids) > 0:
             # We know this hosts's nids, and which nids are secondaries for this target,
             # so we can work out whether we're primary by a process of elimination
             failover_nids = []
             for failover_str in local_target_info['params']['failover.node']:
                 failover_nids.extend(failover_str.split(","))
             failover_nids = set(normalize_nids(failover_nids))

             primary = not (local_nids & failover_nids)
        else:
             # If we got no local NID info, and the target has some failnode info, then
             # error out because we can't figure out whether we're primary.
             raise NoLNetInfo("Cannot setup target %s without LNet info" % local_target_info['name'])
  
        return primary


    def nids_to_mgs(self, nid_strings):
        """Return a ManagementTarget or raise ManagementTarget.DoesNotExist"""
        if set(nid_strings) == set(["0@lo"]) or len(nid_strings) == 0:
            return ManagementTarget.objects.get(targetmount__host = self.host)

        from django.db.models import Count
        nids = Nid.objects.values('nid_string').filter(nid_string__in = nid_strings).annotate(Count('id'))
        unique_nids = [n['nid_string'] for n in nids if n['id__count'] == 1]

        if len(unique_nids) == 0:
            audit_log.warning("nids_to_mgs: No unique NIDs among %s!" % nids)
        hosts = list(Host.objects.filter(nid__nid_string__in = unique_nids).distinct())
        try:
            mgs = ManagementTarget.objects.distinct().get(targetmount__host__in = hosts)
        except ManagementTarget.MultipleObjectsReturned:
            audit_log.error("Unhandled case: two MGSs have mounts on host(s) %s for nids %s" % (hosts, unique_nids))
            # TODO: detect and report the pathological case where someone has given
            # us two NIDs that refer to different hosts which both have a 
            # targetmount for a ManagementTarget, but they're not the
            # same ManagementTarget.
            raise ManagementTarget.DoesNotExist

        return mgs

    def is_valid(self):
        try:
            assert(isinstance(self.host_data, dict))
            assert(self.host_data.has_key('lnet_up'))
            assert(self.host_data.has_key('lnet_loaded'))
            assert(self.host_data.has_key('mgs_targets'))
            assert(self.host_data.has_key('local_targets'))
            assert(self.host_data.has_key('metrics'))
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    @transaction.commit_on_success
    def audit_complete(self, host_id, host_data):
        host = Host.objects.get(pk = host_id)
        # Inside our audit update transaction, check that the host isn't
        # deleted to avoid raising alerts for a deleted host
        if not host.not_deleted:
            return

        self.host = host
        self.host_data = host_data

        if isinstance(host_data, Exception):
            audit_log.error("exception contacting %s: %s" % (self.host, host_data))
            contact = False
        elif not self.is_valid():
            audit_log.error("invalid output from %s: %s" % (self.host, host_data))
            contact = False
        else:
            try:
                from configure.lib.state_manager import StateManager
                from configure.models import StatefulObject
            except ImportError:
                StateManager = None
            if StateManager:
                host = self.host.downcast()
                if isinstance(host, StatefulObject):
                    state = {(False, False): 'lnet_unloaded',
                            (True, False): 'lnet_down',
                            (True, True): 'lnet_up'}[(host_data['lnet_loaded'], host_data['lnet_up'])]
                    StateManager.notify_state(self.host.downcast(), state, ['lnet_unloaded', 'lnet_down', 'lnet_up'])
            LNetOfflineAlert.notify(self.host, not host_data['lnet_up'])
            contact = True

            # Update the Nids associated with each Host
            self.learn_nids()

            # Create Filesystem and Target objects
            self.learn_mgs_info()

            # Create TargetMount objects
            self.learn_target_mounts()

            # Set 'mounted' status on Target objects
            self.learn_target_states()

            # Create and get state of Client objects
            self.learn_clients()

            # Store received metrics
            self.store_metrics()

            # We will update StateManager if it is present
            try:
                from configure.lib.state_manager import StateManager
            except ImportError:
                StateManager = None

            # Loop over all mountables we expected on this host, whether they
            # were actually seen in the results or not.
            for mountable in Mountable.objects.filter(host = self.host):
                if not mountable in self.audited_mountables:
                    # We didn't find this mountable, it must be unmounted
                    mounted = False
                else:
                    # We found this mountable and know its state
                    mounted = self.audited_mountables[mountable]

                # Update AlertStates
                if isinstance(mountable, TargetMount) and not mountable.primary:
                    FailoverActiveAlert.notify(mountable, mounted)
                else:
                    MountableOfflineAlert.notify(mountable, not mounted)

                # Update StatefulObjects
                if StateManager and isinstance(mountable, StatefulObject):
                    state = {False: 'unmounted', True: 'mounted'}[mounted]
                    # TODO: notify StateManager of which targetmount is active
                    # for a given Target
                    #StateManager.notify_state(mountable, state, ['mounted', 'unmounted'])

        HostContactAlert.notify(self.host, not contact)

        return contact

    def learn_nids(self):
        new_host_nids = set(normalize_nids(self.host_data['lnet_nids']))
        old_host_nids = set([n.nid_string for n in self.host.nid_set.all()])
        create_nids = new_host_nids - old_host_nids
        for n in create_nids:
            self.host.nid_set.create(nid_string = n)

        if len(new_host_nids) > 0:
            delete_nids = old_host_nids - new_host_nids
            self.host.nid_set.filter(nid_string = delete_nids).delete()

    def learn_mgs(self, mgs_local_info):
        try:
            mgs = ManagementTarget.objects.get(targetmount__host = self.host)
        except ManagementTarget.DoesNotExist:
            lunnode = self.get_lun_node_for_target(None, self.host, mgs_local_info['device'])

            try:
                primary = self.is_primary(mgs_local_info)
            except NoLnetInfo:
                audit_log.warning("Cannot set up MGS on %s until LNet is running")
                return None

            try:
                mgs = ManagementTarget.objects.distinct().get(targetmount__block_device__lun = lunnode.lun)
            except ManagementTarget.DoesNotExist:
                mgs = None

            if mgs == None:
                # We didn't find an existing ManagementTarget referring to
                # this LUN, create one
                mgs = ManagementTarget(name = "MGS")
                mgs.save()
                audit_log.info("Learned MGS on %s" % self.host)
                self.learn_event(mgs)

            tm = TargetMount.objects.create(
                    target = mgs,
                    host = self.host,
                    primary = primary,
                    mount_point = mgs_local_info['mount_point'],
                    block_device = lunnode)
            audit_log.info("Learned MGS mount at %s on %s" % (tm.mount_point, tm.host))
            self.learn_event(tm)
            
        return mgs

    def learn_target_mounts(self):
        # We will compare any found target mounts to all known MGSs
        for local_info in self.host_data['local_targets']:
            # We learned all targetmounts for MGSs in learn_mgs
            if local_info['kind'] == 'MGS':
                continue

            # Build a list of MGS nids for this local target
            tgt_mgs_nids = []
            try:
                # NB I'm not sure whether tunefs.lustre will give me 
                # one comma-separated mgsnode, or a series of mgsnode
                # settings, so handle both
                for n in local_info['params']['mgsnode']:
                    tgt_mgs_nids.extend(n.split(","))
            except KeyError:
                # 'mgsnode' doesn't have to be present
                pass
            tgt_mgs_nids = set(normalize_nids(tgt_mgs_nids))

            try:
                mgs = self.nids_to_mgs(tgt_mgs_nids)
            except ManagementTarget.DoesNotExist:
                audit_log.warning("Can't find MGS for target with nids %s" % tgt_mgs_nids)
                continue

            # TODO: detect case where we find a targetmount that matches one 
            # which already exists for a different target, where the other target
            # has no name -- in this case we are overlapping with a blank target
            # that was created during configuration.
            target = self.get_or_create_target(mgs, local_info['name'], local_info['device'])
            if not target:
                continue


            # Match a Target which has the same name as this local target,
            # and uses a filesystem on the same MGS
            # TODO: expand this to cover targets other than FilesystemMember,
            # currently MGS TargetMount is a special case elsewhere
            matched_target = None
            try:
                targets = Target.objects.filter(name = local_info['name'])

                for target in targets:
                    if isinstance(target, FilesystemMember) and target.filesystem.mgs == mgs:
                        matched_target = target
            except Target.DoesNotExist:
                audit_log.warning("Target %s has mount point on %s but has not been detected on any MGS" % (name_val, self.host))

            if not matched_target:
                continue

            try:
                primary = self.is_primary(local_info)
                lunnode = self.get_lun_node_for_target(target, self.host, local_info['device'])
                (tm, created) = TargetMount.objects.get_or_create(target = matched_target,
                        host = self.host, primary = primary,
                        mount_point = local_info['mount_point'],
                        block_device = lunnode)
                if created:
                    audit_log.info("Learned association %d between %s and host %s" % (tm.id, local_info['name'], self.host))
                    self.learn_event(tm)
            except NoLNetInfo:
                audit_log.warning("Cannot set up target %s on %s until LNet is running" % (local_info['name'], self.host))

    def get_lun_node_for_target(self, target, host, path):
        try:
            return LunNode.objects.get(path = path, host = host)
        except LunNode.DoesNotExist:
            if target and target.targetmount_set.count() > 0:
                lun = target.targetmount_set.all()[0].block_device.lun
            else:
                # TODO: get the size from somewhere
                lun = Lun.objects.create(size = 0, shareable = False)
            return LunNode.objects.create(path = path, host = host, lun = lun)

    def get_or_create_target(self, mgs, name, device_node_path):
        if name.find("-MDT") != -1:
            klass = MetadataTarget
        elif name.find("-OST") != -1:
            klass = ObjectStoreTarget

        fsname = name.split("-")[0]
        try:
            filesystem = Filesystem.objects.get(name = fsname, mgs = mgs)
        except Filesystem.DoesNotExist:
            audit_log.warning("Encountered target for unknown filesystem %s on mgs %s" % (fsname, mgs.primary_server()))
            return None

        try:
            # Is it an already detected or configured target?
            target_mount = TargetMount.objects.get(block_device__path = device_node_path, host = self.host)
            target = target_mount.target
            if target.name == None:
                target.name = name
                target.save()
                audit_log.info("Learned name for configured target %s" % (target))

            return target
        except TargetMount.DoesNotExist:
            # We are detecting a target anew, or detecting a new mount for an already-named target
            candidates = Target.objects.filter(name = name)
            for target in candidates:
                if isinstance(target, FilesystemMember) and target.filesystem.mgs.downcast() == mgs:
                    return target

            # Fall through, no targets with that name exist on this MGS
            target = klass(name = name, filesystem = filesystem)
            target.save()
            audit_log.info("%s %s %s" % (mgs.id, name, device_node_path))
            audit_log.info("Learned %s %s" % (klass.__name__, name))
            self.learn_event(target)
            return target

    def learn_event(self, learned_item):
        from logging import INFO
        LearnEvent(severity = INFO, host = self.host, learned_item = learned_item).save()

    def learn_target_states(self):
        for mount_info in self.host_data['local_targets']:
            if mount_info['kind'] == 'MGS':
                try:
                    target = ManagementTarget.get_by_host(self.host)
                except ManagementTarget.DoesNotExist:
                    audit_log.error("No Managementtarget for host %s, but it reports an MGS target" % self.host)
                    continue
                mountable = target.targetmount_set.get(
                        host = self.host,
                        mount_point = mount_info['mount_point']).downcast()

            else:
                if mount_info['params'].has_key('mgsnode') and mount_info['params']['mgsnode'] != ("0@lo",):
                    # Find the MGS based on mount_info['params']['mgsnode']
                    mgsnode_nids = normalize_nids(mount_info['params']['mgsnode'][0].split(","))
                    try:
                        mgs = self.nids_to_mgs(mgsnode_nids)
                    except ManagementTarget.DoesNotExist:
                        audit_log.warning("Cannot find MGS for target %s (nids %s) on host %s" % (mount_info['name'], mgsnode_nids, self.host.address))
                        continue
                else:
                    # The MGS is local
                    try:
                        mgs = ManagementTarget.objects.get(targetmount__host = self.host)
                    except ManagementTarget.DoesNotExist:
                        audit_log.error("Cannot find local MGS for target %s on %s which has no mgsnode param" % (mount_info['name'], self.host))
                        continue

                mountable = None
                for target_val in Target.objects.filter(name = mount_info['name']):
                    if not isinstance(target_val, FilesystemMember):
                        continue

                    if target_val.filesystem.mgs.downcast() == mgs.downcast():
                        try:
                            mountable = target_val.targetmount_set.get(host = self.host,
                                            mount_point = mount_info['mount_point'])
                        except:
                            mountable = None
                        break

                if mountable == None:
                    audit_log.warning("Cannot find target %s for mgs %d" % (mount_info['name'], mgs.id))
                    continue

                recovering = TargetMountRecoveryInfo.update(mountable, mount_info["recovery_status"])
                TargetRecoveryAlert.notify(mountable, recovering)

            self.audited_mountables[mountable.downcast()] = mount_info['running']

            # Sync the learned parameters to TargetParam
            TargetParam.update_params(mountable.target, mount_info['params'])

        # If we got some corosync resource information, use it to update ManagedTarget
        try:
            from configure.models import ManagedTarget, ManagedHost, ManagedTargetMount
            from configure.lib.state_manager import StateManager
            configure_enable = True
        except ImportError:
            configure_enable = False

        # TODO: get rid of confusing situation of having ManagedTarget.active_mount for configured systems, but relying on 
        # TargetMount Alerts for unconfigured systems (because they may well not have the corosync stuff we check here, and
        # even if they do, we can't expect that their resources are named the way we name them (HYD-231)
        if configure_enable and self.host_data['resource_locations'] and ManagedTargetMount.objects.filter(host = self.host).count() > 0:
            # There are hydra-configured mounts on this host, and we got some corosync resource information
            for resource_name, node_name in self.host_data['resource_locations'].items():
                try:
                    try:
                        # Parse a resource name like "MGS_2"
                        target_name, target_pk = resource_name.rsplit("_", 1)
                    except ValueError:
                        audit_log.warning("Malformed resource name '%s'" % resource_name)
                        continue
                    target = Target.objects.get(name = target_name, pk = target_pk).downcast()
                except Target.DoesNotExist:
                    audit_log.warning("Resource %s on host %s is not a known target" % (resource_name, self.host))
                    continue

                if node_name == None:
                    active_mount = None
                else:
                    try: 
                        host = ManagedHost.objects.get(address = node_name)
                        try:
                            active_mount = ManagedTargetMount.objects.get(target = target, host = host)
                        except ManagedTargetMount.DoesNotExist:
                            audit_log.warning("Resource for target '%s' is running on host '%s', but there is no such TargetMount" % (target, host))
                            active_mount = None
                    except ManagedHost.DoesNotExist:
                        audit_log.warning("Resource location node '%s' does not match any Host" % (node_name))
                        active_mount = None

                # If we're operating on a Managed* rather than a purely monitored target
                if hasattr(target, 'active_mount'):
                    if active_mount != target.active_mount:
                        target.active_mount = active_mount
                        target.save()

                    state = ['unmounted', 'mounted'][active_mount != None]
                    StateManager.notify_state(target, state, ['mounted', 'unmounted'])

    def learn_clients(self):
        for mount_point, client_info in self.host_data['client_mounts'].items():
            # Find the MGS
            try:
                # Lustre lets you use either
                # a comma or a colon as a delimiter
                nids = re.split("[:,]", client_info['nid'])
                client_mgs_nids = set(normalize_nids(nids))
                mgs = self.nids_to_mgs(client_mgs_nids)
            except ManagementTarget.DoesNotExist:
                audit_log.warning("Ignoring client mount for unknown mgs %s" % client_info['nid'])
                continue

            # Find the filesystem
            try:
                fs = Filesystem.objects.get(name = client_info['filesystem'], mgs = mgs)
            except Filesystem.DoesNotExist:
                audit_log.warning("Ignoring client mount for unknown filesystem '%s' on %s" % (client_info['filesystem'], self.host))
                continue

            # Instantiate Client
            (client, created) = Client.objects.get_or_create(
                    host = self.host, mount_point = mount_point, filesystem = fs)
            if created:
                audit_log.info("Learned client %s" % client)
                self.learn_event(client)

            self.audited_mountables[client.downcast()] = client_info['mounted']

    def learn_mgs_info(self):
        found_mgs = False
        for volume in self.host_data['local_targets']:
            if volume['kind'] == "MGS":
                found_mgs = True
                mgs_local_info = volume
        if not found_mgs:
            return

        # Learn an MGS target and a TargetMount for this host
        mgs = self.learn_mgs(mgs_local_info)
        if not mgs:
            return

        # Create Filesystem objects for all those in this MGS
        for fs_name, targets in self.host_data['mgs_targets'].items():
            (fs, created) = Filesystem.objects.get_or_create(name = fs_name, mgs = mgs)
            if created:
                audit_log.info("Learned filesystem '%s'" % fs_name)
                self.learn_event(fs)

    def store_lustre_target_metrics(self, target_name, metrics):
        # TODO: Re-enable MGS metrics storage if it turns out it's useful.
        if target_name == "MGS":
            return

        try:
            target = Target.objects.get(name=target_name,
                                        targetmount__host=self.host)
        except Target.DoesNotExist:
            # Unknown target -- ignore metrics
            audit_log.warning("Discarding metrics for unknown target: %s" % target_name)
            return

        target.downcast().metrics.update(metrics)

    def store_node_metrics(self, metrics):
        self.host.downcast().metrics.update(metrics)

    def store_metrics(self):
        """
        Pass the received metrics into the metrics library for storage.
        """
        raw_metrics = self.host_data['metrics']['raw']

        try:
            node_metrics = raw_metrics['node']
            try:
                node_metrics['lnet'] = raw_metrics['lustre']['lnet']
            except KeyError:
                pass

            self.store_node_metrics(node_metrics)
        except KeyError:
            pass

        try:
            for target in raw_metrics['lustre']['target']:
                target_metrics = raw_metrics['lustre']['target'][target]
                self.store_lustre_target_metrics(target, target_metrics)
        except KeyError:
            pass
