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
from configure.models import *
from django.db import transaction

import re

import logging
audit_log = logging.getLogger('audit')
audit_log.setLevel(logging.DEBUG)
handler = logging.FileHandler(settings.AUDIT_LOG_PATH)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
audit_log.addHandler(handler)
if settings.DEBUG:
    audit_log.setLevel(logging.DEBUG)
else:
    audit_log.setLevel(logging.INFO)

def nids_to_mgs(host, nid_strings):
    """nid_strings: nids of a target.  host: host on which the target was seen.
    Return a ManagedMgs or raise ManagedMgs.DoesNotExist"""
    if set(nid_strings) == set(["0@lo"]) or len(nid_strings) == 0:
        return ManagedMgs.objects.get(targetmount__host = self.host)

    from django.db.models import Count
    nids = Nid.objects.values('nid_string').filter(nid_string__in = nid_strings).annotate(Count('id'))
    unique_nids = [n['nid_string'] for n in nids if n['id__count'] == 1]

    if len(unique_nids) == 0:
        audit_log.warning("nids_to_mgs: No unique NIDs among %s!" % nids)
    hosts = list(ManagedHost.objects.filter(lnetconfiguration__nid__nid_string__in = unique_nids).distinct())
    try:
        mgs = ManagedMgs.objects.distinct().get(managedtargetmount__host__in = hosts)
    except ManagedMgs.MultipleObjectsReturned:
        audit_log.error("Unhandled case: two MGSs have mounts on host(s) %s for nids %s" % (hosts, unique_nids))
        # TODO: detect and report the pathological case where someone has given
        # us two NIDs that refer to different hosts which both have a 
        # targetmount for a ManagedMgs, but they're not the
        # same ManagedMgs.
        raise ManagedMgs.DoesNotExist

    return mgs

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


class UpdateScan(object):
    def __init__(self):
        self.audited_mountables = {}
        self.host = None
        self.host_data = None

    def is_valid(self):
        try:
            assert(isinstance(self.host_data, dict))
            assert(self.host_data.has_key('lnet_up'))
            assert(self.host_data.has_key('lnet_loaded'))
            assert(self.host_data.has_key('mounts'))
            assert(self.host_data.has_key('metrics'))
            assert(self.host_data.has_key('resource_locations'))
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    @transaction.commit_on_success
    def run(self, host_id, host_data):
        host = ManagedHost.objects.get(pk=host_id)
        self.host = host

        # Possible that we were started just before a host was deleted: 
        # avoid raising alerts for deleted hosts by doing this check inside 
        # our transaction
        if not host.not_deleted:
            return

        self.host_data = host_data

        if isinstance(host_data, Exception):
            audit_log.error("exception contacting %s: %s" % (self.host, host_data))
            contact = False
        elif not self.is_valid():
            audit_log.error("invalid output from %s: %s" % (self.host, host_data))
            contact = False
        else:
            contact = True

            # Get state of Client objects
            #self.learn_clients()

            self.store_metrics()
            self.update_lnet()
            self.update_resource_locations()
            self.update_target_mounts()

        HostContactAlert.notify(self.host, not contact)

    def update_lnet(self):
        # Update LNet status
        from configure.lib.state_manager import StateManager
        state = {(False, False): 'lnet_unloaded',
                (True, False): 'lnet_down',
                (True, True): 'lnet_up'}[(self.host_data['lnet_loaded'], self.host_data['lnet_up'])]
        StateManager.notify_state(self.host.downcast(), state, ['lnet_unloaded', 'lnet_down', 'lnet_up'])
        # Update LNet alerts
        # TODO: also set the alert status in Job completions when the state is changed,
        # rather than waiting for this scan to notice.
        LNetOfflineAlert.notify(self.host, not self.host_data['lnet_up'])

    def update_target_mounts(self):
        # Loop over all mountables we expected on this host, whether they
        # were actually seen in the results or not.
        mounted_uuids = dict([(m['fs_uuid'], m) for m in self.host_data['mounts']])
        for target_mount in ManagedTargetMount.objects.filter(host = self.host):

            # Mounted-ness
            # ============
            mounted_locally = target_mount.target.uuid in mounted_uuids

            # Recovery status
            # ===============
            if mounted_locally:
                mount_info = mounted_uuids[target_mount.target.uuid]
                recovery_status = mount_info["recovery_status"]
            else:
                recovery_status = {}

            # Update to active_mount and alerts for autodetected 
            # targets done here instead of resource_locations
            if target_mount.target.state == 'autodetected':
                target = target_mount.target
                if mounted_locally:
                    target.set_active_mount(target_mount)
                elif not mounted_locally and target.active_mount == target_mount:
                    target.set_active_mount(None)

            if target_mount.target.active_mount == None:
                TargetRecoveryInfo.update(target_mount.target, {})
                TargetRecoveryAlert.notify(target_mount.target, False)
            elif mounted_locally:
                recovering = TargetRecoveryInfo.update(target_mount.target, recovery_status)
                TargetRecoveryAlert.notify(target_mount.target, recovering)

    def update_resource_locations(self):
        if self.host_data['resource_locations'] == None:
            # None here means that it was not possible to obtain a 
            # list from corosync: corosync may well be absent if
            # we're monitoring a non-hydra-managed autodetected 
            # system.  But if there are non-autodetected mounts
            # then this is a problem.
            from django.db.models import Q
            if ManagedTargetMount.objects.filter(~Q(state = 'autodetected'), host = self.host).count() > 0:
                audit_log.error("Got no resource_locations from host %s, but there are hydra-configured mounts on that server!" % self.host)
            return

        for resource_name, node_name in self.host_data['resource_locations'].items():
            try:
                try:
                    # Parse a resource name like "MGS_2"
                    target_name, target_pk = resource_name.rsplit("_", 1)
                except ValueError:
                    audit_log.warning("Malformed resource name '%s'" % resource_name)
                    continue
                target = ManagedTarget.objects.get(name = target_name, pk = target_pk).downcast()
            except ManagedTarget.DoesNotExist:
                audit_log.warning("Resource %s on host %s is not a known target" % (resource_name, self.host))
                continue

            # If we're operating on a Managed* rather than a purely monitored target
            if target.state != 'autodetected':
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

                target.set_active_mount(active_mount)

                state = ['unmounted', 'mounted'][active_mount != None]
                from configure.lib.state_manager import StateManager
                StateManager.notify_state(target, state, ['mounted', 'unmounted'])

    def store_lustre_target_metrics(self, target_name, metrics):
        # TODO: Re-enable MGS metrics storage if it turns out it's useful.
        if target_name == "MGS":
            return

        try:
            target = ManagedTarget.objects.get(name=target_name,
                                        managedtargetmount__host=self.host)
        except ManagedTarget.DoesNotExist:
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


class DetectScan(object):
    def __init__(self):
        self.raw_data = None
        self.target_locations = None

    @transaction.commit_on_success
    def run(self, host_id, host_data, all_hosts_data):
        host = ManagedHost.objects.get(pk = host_id)
        # Inside our audit update transaction, check that the host isn't
        # deleted to avoid raising alerts for a deleted host
        if not host.not_deleted:
            return

        self.host = host
        self.host_data = host_data
        self.all_hosts_data = all_hosts_data

        if isinstance(host_data, Exception):
            audit_log.error("exception contacting %s: %s" % (self.host, host_data))
            contact = False
        elif not self.is_valid():
            audit_log.error("invalid output from %s: %s" % (self.host, host_data))
            contact = False
        else:
            contact = True

            # Create Filesystem and Target objects
            self.learn_mgs_info()

            # Create TargetMount objects
            self.learn_target_mounts()

                # Configuration params
                # ====================
 #               if mounted_locally:
 #                   TargetParam.update_params(target_mount.target, mount_info['params'])

        return contact
    
    def is_primary(self, local_target_info):
        if self.host.lnetconfiguration.state != 'nids_known':
             raise NoLNetInfo("Cannot setup target %s without LNet info" % local_target_info['name'])

        local_nids = set(self.host.lnetconfiguration.get_nids())

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
  
        return primary

    def is_valid(self):
        try:
            assert(isinstance(self.host_data, dict))
            assert(self.host_data.has_key('mgs_targets'))
            assert(self.host_data.has_key('local_targets'))
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    def learn_mgs(self, mgs_local_info):
        try:
            mgs = ManagedMgs.objects.get(uuid = mgs_local_info['uuid'])
            try:
                tm = ManagedTargetMount.objects.get(target = mgs, host = self.host)
            except ManagedTargetMount.DoesNotExist:
                lunnode = self.get_lun_node_for_target(None, self.host, mgs_local_info['device'])
                primary = self.is_primary(mgs_local_info)
                tm = ManagedTargetMount.objects.create(
                        state = 'autodetected',
                        target = mgs,
                        host = self.host,
                        primary = primary,
                        block_device = lunnode)
        except ManagedMgs.DoesNotExist:
            # Only do this for possibly-primary mounted MGSs
            # Otherwise would risk seeing an MGS somewhere it's not actually
            # used and assuming that that was the primary location.
            if not self.is_primary(mgs_local_info) or not mgs_local_info['mounted']:
                return None

            try:
                mgs = ManagedMgs.objects.get(managedtargetmount__host = self.host)
                raise RuntimeError("Multiple MGSs on host %s" % host)
            except ManagedMgs.DoesNotExist:
                pass

            lunnode = self.get_lun_node_for_target(None, self.host, mgs_local_info['device'])

            primary = self.is_primary(mgs_local_info)

            # We didn't find an existing ManagedMgs referring to
            # this LUN, create one
            mgs = ManagedMgs(uuid = mgs_local_info['uuid'], name = "MGS", state = 'autodetected')
            mgs.save()
            audit_log.info("Learned MGS on %s" % self.host)
            self.learn_event(mgs)

            tm = ManagedTargetMount.objects.create(
                    state = 'autodetected',
                    target = mgs,
                    host = self.host,
                    primary = primary,
                    block_device = lunnode)
            audit_log.info("Learned MGS mount %s" % (tm.host))
            self.learn_event(tm)
            
        return mgs

    def target_available_here(self, mgs, local_info):
        target_nids = []
        if local_info['params'].has_key('failover.node'):
            for failover_str in local_info['params']['failover.node']:
                target_nids.extend(failover_str.split(","))
        mgs_host = mgs.primary_server()
        fs_name, target_name = local_info['name'].rsplit("-", 1)
        try:
            mgs_target_info = None
            for t in self.all_hosts_data[mgs_host]['mgs_targets'][fs_name]:
                if t['name'] == local_info['name']:
                    mgs_target_info = t
            if not mgs_target_info:
                raise KeyError
        except KeyError:
            audit_log.warning("Saw target %s on %s:%s which is not known to mgs %s" % (local_info['name'], self.host, local_info['device'], mgs_host))
            return False
        primary_nid = mgs_target_info['nid']
        target_nids.append(primary_nid)

        target_nids = set(normalize_nids(target_nids))
        if set(self.host.lnetconfiguration.get_nids()) & target_nids:
            return True
        else:
            return False

    def learn_target_mounts(self):
        # We will compare any found target mounts to all known MGSs
        for local_info in self.host_data['local_targets']:
            # We learned all targetmounts for MGSs in learn_mgs
            if local_info['name'] == 'MGS':
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
                mgs = nids_to_mgs(self.host, tgt_mgs_nids)
            except ManagedMgs.DoesNotExist:
                audit_log.warning("Can't find MGS for target with nids %s" % tgt_mgs_nids)
                continue

            if not self.target_available_here(mgs, local_info):
                audit_log.warning("Ignoring %s on %s, as it is not mountable on this host" % (local_info['name'], self.host))
                continue

            # TODO: detect case where we find a targetmount that matches one 
            # which already exists for a different target, where the other target
            # has no name -- in this case we are overlapping with a blank target
            # that was created during configuration.
            target = self.get_or_create_target(mgs, local_info)
            if not target:
                continue


            # Match a Target which has the same name as this local target,
            # and uses a filesystem on the same MGS
            # TODO: expand this to cover targets other than FilesystemMember,
            # currently MGS TargetMount is a special case elsewhere
            matched_target = None
            try:
                targets = ManagedTarget.objects.filter(name = local_info['name'])

                for target in targets:
                    if isinstance(target, FilesystemMember) and target.filesystem.mgs == mgs:
                        matched_target = target
            except ManagedTarget.DoesNotExist:
                audit_log.warning("Target %s has mount point on %s but has not been detected on any MGS" % (name_val, self.host))

            if not matched_target:
                continue

            try:
                primary = self.is_primary(local_info)
                lunnode = self.get_lun_node_for_target(target, self.host, local_info['device'])
                (tm, created) = ManagedTargetMount.objects.get_or_create(target = matched_target,
                        host = self.host, primary = primary,
                        block_device = lunnode)
                if created:
                    tm.state = 'autodetected'
                    tm.save()
                    audit_log.info("Learned association %d between %s and host %s" % (tm.id, local_info['name'], self.host))
                    self.learn_event(tm)
            except NoLNetInfo:
                audit_log.warning("Cannot set up target %s on %s until LNet is running" % (local_info['name'], self.host))

    def get_lun_node_for_target(self, target, host, path):
        # TODO: tighter integration with storage resource discovery, so that we never have
        # to create our own LunNodes: we would need to ensure that this wasn't executed
        # until resources were discovered (or run a discovery step synchronously in here
        # by messaging the resource manager), and then make sure the agent refered to
        # devices by the same name as the storage resources.

        # Get-or-create like logic: try getting it, then try inserting it, and
        # if insertion failed then we collided, so try getting again.
        from django.db import IntegrityError
        try:
            return self._get_lun_node_for_target(target, host, path)
        except IntegrityError:
            return self._get_lun_node_for_target(target, host, path)

    def _get_lun_node_for_target(self, target, host, path):
        try:
            return LunNode.objects.get(path = path, host = host)
        except LunNode.DoesNotExist:
            if target and target.managedtargetmount_set.count() > 0:
                lun = target.managedtargetmount_set.all()[0].block_device.lun
            else:
                # TODO: get the size from somewhere
                lun = Lun.objects.create(size = 0, shareable = False)
            return LunNode.objects.create(path = path, host = host, lun = lun)

    def get_or_create_target(self, mgs, local_info):
        name = local_info['name']
        device_node_path = local_info['device']
        uuid = local_info['uuid']

        if name.find("-MDT") != -1:
            klass = ManagedMdt
        elif name.find("-OST") != -1:
            klass = ManagedOst

        fsname = re.search("([\w\-]+)-\w+", name).group(1)
        try:
            filesystem = ManagedFilesystem.objects.get(name = fsname, mgs = mgs)
        except ManagedFilesystem.DoesNotExist:
            audit_log.warning("Encountered target (%s) for unknown filesystem %s on mgs %s" % (name, fsname, mgs.primary_server()))
            return None

        try:
            # Is it an already detected or configured target?
            target_mount = ManagedTargetMount.objects.get(block_device__path = device_node_path, host = self.host)
            target = target_mount.target
            if target.name == None:
                target.name = name
                target.save()
                audit_log.info("Learned name for configured target %s" % (target))

            return target
        except ManagedTargetMount.DoesNotExist:
            # We are detecting a target anew, or detecting a new mount for an already-named target
            candidates = ManagedTarget.objects.filter(name = name)
            for target in candidates:
                if isinstance(target, FilesystemMember) and target.filesystem.mgs.downcast() == mgs:
                    return target

            # Fall through, no targets with that name exist on this MGS
            target = klass(uuid = uuid, name = name, filesystem = filesystem, state = 'autodetected')
            target.save()
            audit_log.info("%s %s %s" % (mgs.id, name, device_node_path))
            audit_log.info("Learned %s %s" % (klass.__name__, name))
            self.learn_event(target)
            return target

    def learn_event(self, learned_item):
        from logging import INFO
        LearnEvent(severity = INFO, host = self.host, learned_item = learned_item).save()

    def learn_clients(self):
        for mount_point, client_info in self.host_data['client_mounts'].items():
            # Find the MGS
            try:
                # Lustre lets you use either
                # a comma or a colon as a delimiter
                nids = re.split("[:,]", client_info['nid'])
                client_mgs_nids = set(normalize_nids(nids))
                mgs = nids_to_mgs(self.host, client_mgs_nids)
            except ManagedMgs.DoesNotExist:
                audit_log.warning("Ignoring client mount for unknown mgs %s" % client_info['nid'])
                continue

            # Find the filesystem
            try:
                fs = ManagedFilesystem.objects.get(name = client_info['filesystem'], mgs = mgs)
            except ManagedFilesystem.DoesNotExist:
                audit_log.warning("Ignoring client mount for unknown filesystem '%s' on %s" % (client_info['filesystem'], self.host))
                continue

            # Instantiate Client
            (client, created) = Client.objects.get_or_create(
                    host = self.host, mount_point = mount_point, filesystem = fs)
            if created:
                audit_log.info("Learned client %s" % client)
                self.learn_event(client)

            # TODO: sort out client monitoring
            #self.audited_mountables[client.downcast()] = client_info['mounted']

    def learn_mgs_info(self):
        found_mgs = False
        for volume in self.host_data['local_targets']:
            if volume['name'] == "MGS":
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
            (fs, created) = ManagedFilesystem.objects.get_or_create(name = fs_name, mgs = mgs)
            if created:
                audit_log.info("Learned filesystem '%s'" % fs_name)
                self.learn_event(fs)


