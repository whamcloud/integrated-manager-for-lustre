#!/usr/bin/env python
from django.core.management import setup_environ
import settings
setup_environ(settings)

# Access to 'monitor' database
from monitor.models import *

import re
import sys
import traceback
import simplejson as json

from logging import getLogger, FileHandler, StreamHandler, INFO
getLogger(__name__).setLevel(INFO)
getLogger(__name__).addHandler(FileHandler("%s.log" % __name__))
if settings.DEBUG:
    getLogger(__name__).addHandler(StreamHandler())

def log():
    return getLogger(__name__)

class HostAuditError(Exception):
    def __init__(self, host, *args, **kwargs):
        self.host = host
        super(HostAuditError, self).__init__(*args, **kwargs)

AGENT_PATH = "/usr/bin/hydra-agent.py"

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
        self.audit = None
    
    def discover_hosts(self):
        import os
        for host_name in os.popen("cerebro-stat -m cluster_nodes").readlines():
            if host_name.find('=') != -1:
                # Cerebro 1.12 puts a "MODULE DIR =" line at the start of 
                # cerebro-stat's output: skip lines like that
                continue

            host_name = host_name.rstrip()

            # Use 'configure' application if it's available
            try:
                from configure.models import ManagedHost
                host, created = ManagedHost.objects.get_or_create(address = host_name)
            except ImportError:
                host, created = Host.objects.get_or_create(address = host_name)

            if created:
                log().info("Discovered host %s from cerebro" % host_name)
                from logging import INFO
                LearnEvent(severity = INFO, host = host, learned_item = host).save()

            try:
                sm = host.monitor
            except Monitor.DoesNotExist:
                sm = SshMonitor(host = host)
                sm.save()

    def is_primary(self, local_target_info):
        local_nids = [n.nid_string for n in self.host.nid_set.all()]

        if not local_target_info['params'].has_key('failover.node'):
             # If the target has no failover nodes, then it is accessed by only 
             # one (primary) host, i.e. this one
             primary = True
        elif len(local_nids) > 0:
             # We know this hosts's nids, and which nids are secondaries for this target,
             # so we can work out whether we're primary by a process of elimination
             secondary_nids = set(normalize_nids(local_target_info['params']['failover.node']))
             primary = True
             for nid in local_nids:
                 if nid in secondary_nids:
                     primary = False
        else:
             # If we got no local NID info, and the target has some failnode info, then
             # error out because we can't figure out whether we're primary.
             raise NoLNetInfo("Cannot setup target %s without LNet info" % local_target_info['name'])
  
        return primary


    def nids_to_mgs(self, nid_strings):
        """Return a ManagementTarget or raise ManagementTarget.DoesNotExist"""
        if set(nid_strings) == set(["0@lo"]) or len(nid_strings) == 0:
            return ManagementTarget.objects.get(targetmount__host = self.host)

        nids = Nid.objects.filter(nid_string__in = nid_strings)
        # Limit selecting nids to unique ones
        nids = [n for n in nids if Nid.objects.filter(nid_string = n.nid_string).count() == 1]
        hosts = Host.objects.filter(nid__in = nids)
        try:
            mgs = ManagementTarget.objects.get(targetmount__host__in = hosts)
        except ManagementTarget.MultipleObjectsReturned:
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
            assert(self.host_data.has_key('device_nodes'))
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    def audit_complete(self, audit, host_data):
        self.audit = audit
        self.host = audit.host
        self.host_data = host_data

        if isinstance(host_data, Exception):
            log().error("exception contacting %s: %s" % (self.host, host_data))
            contact = False
        elif not self.is_valid():
            log().error("invalid output from %s: %s" % (self.host, host_data))
            contact = False
        else:
            self.audit.lnet_up = host_data['lnet_up']
            self.audit.save()

            try:
                from configure.lib.state_manager import StateManager
            except ImportError:
                StateManager = None
            if StateManager:
                state = {(False, False): 'lnet_unloaded',
                        (True, False): 'lnet_down',
                        (True, True): 'lnet_up'}[(host_data['lnet_loaded'], host_data['lnet_up'])]
                StateManager.notify_state(self.host.downcast(), state, ['lnet_unloaded', 'lnet_down', 'lnet_up'])
            LNetOfflineAlert.notify(self.host, not host_data['lnet_up'])
            contact = True

            # Update the Nids associated with each Host
            self.learn_nids()

            # Update device nodes known on this Host
            self.learn_device_nodes()

            # Create Filesystem and Target objects
            self.learn_fs_targets()

            # Create TargetMount objects
            self.learn_target_mounts()

            # Set 'mounted' status on Target objects
            self.learn_target_states()

            # Create and get state of Client objects
            self.learn_clients()

            # Any TargetMounts which we didn't get data for may need to emit offline events
            # Also use this loop to update StateManager
            try:
                from configure.lib.state_manager import StateManager
            except ImportError:
                StateManager = None

            for mountable in Mountable.objects.filter(host = self.host):
                try:
                    audit_mountable = AuditMountable.objects.get(
                            audit = self.audit, mountable = mountable)

                except AuditMountable.DoesNotExist:
                    if isinstance(mountable, TargetMount) and not mountable.primary:
                        FailoverActiveAlert.notify(mountable, False)
                    else:
                        MountableOfflineAlert.notify(mountable, True)
                    audit_mountable = AuditMountable(audit = self.audit,
                            mountable = mountable, mounted = False)
                    audit_mountable.save()

                if StateManager:
                    # FIXME: potentially get confused with a removed 
                    # targetmount, need to only do this update if the
                    # targetmount is not in a 'deleted' state.
                    state = {True: 'mounted', False: 'unmounted'}[audit_mountable.mounted]
                    StateManager.notify_state(mountable, state, ['mounted', 'unmounted'])

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

    def learn_device_nodes(self):
        for node_info in self.host_data['device_nodes']:
            try:
                existing_node = LunNode.objects.get(path = node_info['path'], host = self.host)
                if len(node_info['fs_uuid']) > 0:
                    if existing_node.lun and existing_node.lun.fs_uuid != node_info['fs_uuid']:
                        existing_node.lun.fs_uuid = node_info['fs_uuid']
                        existing_node.save()
                    elif not existing_node.lun:
                        lun, created = Lun.objects.get_or_create(fs_uuid = node_info['fs_uuid'])
                        existing_node.lun = lun
                        existing_node.save()
                        log().info("Associated lun %s with node %s" % (lun, existing_node))

            except LunNode.DoesNotExist:
                if len(node_info['fs_uuid']) > 0:
                    lun, created = Lun.objects.get_or_create(fs_uuid = node_info['fs_uuid'])
                    if created:
                        log().info("Discovered Lun %s" % (lun))
                else:
                    # Create LunNodes with no Lun when there is no unique ID for the Lun available
                    lun = None
                node = LunNode(
                        lun = lun,
                        host = self.host,
                        path = node_info['path'],
                        used_hint = node_info['used'])
                node.save()
                log().info("Discovered node %s (lun %s)" % (node, lun))

        for tm in TargetMount.objects.filter(host = self.host, primary = False, block_device = None):
            lun = tm.target.targetmount_set.get(primary = True).block_device.lun
            if not lun:
                continue
            try:
                node = LunNode.objects.get(lun = lun, host = self.host)
                tm.block_device = node
                tm.save()
                log().info("Associated failover target mount %s:%s with node %s" % (tm.host, tm, node))
            except LunNode.DoesNotExist:
                pass

    def learn_mgs(self, mgs_local_info):
        try:
            mgs = ManagementTarget.objects.get(targetmount__host = self.host)
        except ManagementTarget.DoesNotExist:
            # FIXME: when there is no LNet info for self.host, we cannot be 
            # sure if this is a new MGS or a failover for an existing one
            existing_mgs = None
            for mgs in ManagementTarget.objects.all():
                if mgs_local_info['params'].has_key('failover.node'):
                    failovers = set(normalize_nids(mgs.get_param('failover.node')))
                    local_nids = set(normalize_nids([n.nid_string for n in self.host.nid_set.all()]))
                    if local_nids & failovers:
                        existing_mgs = mgs
                        break

            if not existing_mgs:
                mgs = ManagementTarget(name = "MGS")
                mgs.save()
                log().info("Learned MGS on %s" % self.host)
                self.learn_event(mgs)
            else:
                mgs = existing_mgs

            try:
                primary = self.is_primary(mgs_local_info)
                try:
                    lunnode = LunNode.objects.get(path = mgs_local_info['device'], host = self.host)
                    tm,created = TargetMount.objects.get_or_create(
                            target = mgs,
                            host = self.host,
                            primary = primary,
                            mount_point = mgs_local_info['mount_point'],
                            block_device = lunnode)
                    if created:
                        log().info("Learned MGS mount on %s" % self.host)
                        self.learn_event(tm)
                except LunNode.DoesNotExist:
                    log().warning("No LunNode for MGS device path '%s'" % mgs_local_info['device'])
            except NoLNetInfo:
                log().warning("Cannot fully set up MGS on %s until LNet is running")

            # Find the local_targets info for the MGS
            #  * if it has no failnode, then this is definitely primary (+ if
            #    it's configured on more than one host then that's an error)
            #  * if it has one or more failnodes, then this is the primary if 
            #    none of the failnode NIDs match a local NID of this host.

            mgs_local_info = None
            for target in self.host_data['local_targets']:
                if target['kind'] == 'MGS':
                    mgs_local_info = target
            if mgs_local_info == None:
                raise RuntimeError("Got mgs_targets but no MGS local_target!")
            
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
                log().warning("Can't find MGS for target with nids %s" % tgt_mgs_nids)
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
                log().warning("Target %s has mount point on %s but has not been detected on any MGS" % (name_val, self.host))

            if not matched_target:
                continue

            try:
                primary = self.is_primary(local_info)
                lunnode = LunNode.objects.get(path = local_info['device'], host = self.host)
                (tm, created) = TargetMount.objects.get_or_create(target = matched_target,
                        host = self.host, primary = primary,
                        mount_point = local_info['mount_point'],
                        block_device = lunnode)
                if created:
                    log().info("Learned association %d between %s and host %s" % (tm.id, local_info['name'], self.host))
                    self.learn_event(tm)
            except LunNode.DoesNotExist:
                log().warning("No LunNode for target device '%s'" % local_info['device'])
            except NoLNetInfo:
                log().warning("Cannot set up target %s on %s until LNet is running" % (local_info['name'], self.address))

    def get_or_create_target(self, mgs, name, device_node_path):
        if name.find("-MDT") != -1:
            klass = MetadataTarget
        elif name.find("-OST") != -1:
            klass = ObjectStoreTarget

        fsname = name.split("-")[0]
        try:
            filesystem = Filesystem.objects.get(name = fsname, mgs = mgs)
        except Filesystem.DoesNotExist:
            log().warning("Encountered target for unknown filesystem %s on mgs %s" % (fsname, mgs.primary_server()))
            return None

        try:
            # Is it an already detected or configured target?
            target_mount = TargetMount.objects.get(block_device__path = device_node_path, host = self.host)
            target = target_mount.target
            if target.name == None:
                target.name = name
                target.save()
                log().info("Learned name for configured target %s" % (target))

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
            log().info("%s %s %s" % (mgs.id, name, device_node_path))
            log().info("Learned %s %s" % (klass.__name__, name))
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
                    log().error("No Managementtarget for host %s, but it reports an MGS target" % selfhost)
                    continue
                mountable = target.targetmount_set.get(host = self.host, mount_point = mount_info['mount_point']).downcast()

                if mountable.primary:
                    MountableOfflineAlert.notify(mountable, not mount_info['running'])
                else:
                    FailoverActiveAlert.notify(mountable, mount_info['running'])

                audit_mountable = AuditMountable(audit = self.audit,
                        mountable = mountable, mounted = mount_info['running'])
            else:
                if mount_info['params'].has_key('mgsnode') and mount_info['params']['mgsnode'] != ("0@lo",):
                    # Find the MGS based on mount_info['params']['mgsnode']
                    mgsnode_nids = normalize_nids(mount_info['params']['mgsnode'][0].split(","))
                    try:
                        mgs = self.nids_to_mgs(mgsnode_nids)
                    except ManagementTarget.DoesNotExist:
                        log().warning("Cannot find MGS for target %s (nids %s) on host %s" % (mount_info['name'], mgsnode_nids, self.host.address))
                        continue
                else:
                    # The MGS is local
                    try:
                        mgs = ManagementTarget.objects.get(targetmount__host = self.host)
                    except ManagementTarget.DoesNotExist:
                        log().error("Cannot find local MGS for target %s on %s which has no mgsnode param" % (mount_info['name'], self.host))
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
                    log().warning("Cannot find target %s for mgs %d" % (mount_info['name'], mgs.id))
                    continue

                audit_mountable = AuditRecoverable(audit = self.audit, 
                        mountable = mountable, mounted = mount_info['running'],
                        recovery_status = json.dumps(mount_info["recovery_status"]))

                if mountable.primary:
                    MountableOfflineAlert.notify(mountable, not mount_info['running'])
                else:
                    FailoverActiveAlert.notify(mountable, mount_info['running'])
                TargetRecoveryAlert.notify(mountable, audit_mountable.is_recovering())

            audit_mountable.save()

            # Sync the learned parameters to TargetParam
            target = audit_mountable.mountable.target
            old_params = set(target.get_params())

            new_params = set()
            for key, value_list in mount_info['params'].items():
                for value in value_list:
                    new_params.add((key, value))
            
            for del_param in old_params - new_params:
                target.targetparam_set.get(key = del_param[0], value = del_param[1]).delete()
                log().info("del_param: %s" % (del_param,))
            for add_param in new_params - old_params:
                target.targetparam_set.create(key = add_param[0], value = add_param[1])
                log().info("add_param: %s" % (add_param,))

    def learn_clients(self):
        for mount_point, client_info in self.host_data['client_mounts'].items():
            # Find the MGS
            try:
                client_mgs_nids = set(normalize_nids(client_info['nid'].split(":")))
                mgs = self.nids_to_mgs(client_mgs_nids)
            except ManagementTarget.DoesNotExist:
                log().warning("Ignoring client mount for unknown mgs %s" % client_info['nid'])
                continue

            # Find the filesystem
            try:
                fs = Filesystem.objects.get(name = client_info['filesystem'], mgs = mgs)
            except Filesystem.DoesNotExist:
                log().warning("Ignoring client mount for unknown filesystem '%s' on %s" % (client_info['filesystem'], self.host))
                continue

            # Instantiate Client
            (client, created) = Client.objects.get_or_create(
                    host = self.host, mount_point = mount_point, filesystem = fs)
            if created:
                log().info("Learned client %s" % client)
                self.learn_event(client)

            MountableOfflineAlert.notify(client, not client_info['mounted'])
            audit_mountable = AuditMountable(audit = self.audit, mountable = client, mounted = client_info['mounted'])
            audit_mountable.save()

    def learn_fs_targets(self):
        found_mgs = False
        for volume in self.host_data['local_targets']:
            if volume['kind'] == "MGS":
                found_mgs = True
                mgs_local_info = volume
        if not found_mgs:
            return

        # Learn an MGS target and a TargetMount for this host
        mgs = self.learn_mgs(mgs_local_info)

        # Create Filesystem objects for all those in this MGS
        filesystem_targets = {}
        for fs_name, targets in self.host_data['mgs_targets'].items():
            (fs, created) = Filesystem.objects.get_or_create(name = fs_name, mgs = mgs)
            if created:
                log().info("Learned filesystem '%s'" % fs_name)
                self.learn_event(fs)
            filesystem_targets[fs] = targets


