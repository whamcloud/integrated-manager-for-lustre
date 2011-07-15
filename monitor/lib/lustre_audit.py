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

AGENT_PATH = "/root/hydra-agent.py"

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
        nids = Nid.objects.filter(nid_string__in = nid_strings)
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

    def audit_complete(self, audit, host_data):
        self.audit = audit
        self.host = audit.host
        self.host_data = host_data

        # Map of AuditHost to output of hydra-agent
        if isinstance(host_data, Exception):
            log().error("bad output from %s: %s" % (self.host, host_data))
            contact = False
        else:
            assert(isinstance(host_data, dict))
            assert(host_data.has_key('lnet_up'))
            # FIXME: we assume any valid JSON we receive is a
            # valid report.  This means we're not very
            # robust in the face of hydra-agent bugs, both here
            # and in subsequent processing on the data

            audit_host = AuditHost(
                    audit = self.audit,
                    lnet_up = host_data['lnet_up'])
            audit_host.save()
            LNetOfflineAlert.notify(self.host, not host_data['lnet_up'])
            contact = True

            # Update the Nids associated with each Host
            self.learn_nids()

            # Create Filesystem and Target objects
            self.learn_fs_targets()

            # Create TargetMount objects
            self.learn_target_mounts()

            # Set 'mounted' status on Target objects
            self.learn_target_states()

            # Create and get state of Client objects
            self.learn_clients()


            # Any TargetMounts which we didn't get data for may need to emit offline events
            for mountable in Mountable.objects.filter(host = self.host):
                try:
                    audited = AuditMountable.objects.get(
                            audit = self.audit, mountable = mountable)
                except AuditMountable.DoesNotExist:
                    MountableOfflineAlert.notify(mountable, True)
                    audit_mountable = AuditMountable(audit = self.audit,
                            mountable = mountable, mounted = False)
                    audit_mountable.save()

        HostContactAlert.notify(self.host, not contact)

    def learn_nids(self):
        new_host_nids = set(normalize_nids(self.host_data['lnet_nids']))
        old_host_nids = set([n.nid_string for n in self.host.nid_set.all()])
        create_nids = new_host_nids - old_host_nids
        for n in create_nids:
            self.host.nid_set.create(nid_string = n)
        if len(new_host_nids) > 0:
            delete_nids = old_host_nids - new_host_nids
            self.host.nid_set.filter(nid_string = delete_nids).delete()

        for nid_str in new_host_nids:
            audit_host = self.audit.audithost_set.get()
            audit_host.auditnid_set.create(nid_string = nid_str)

    def learn_mgs(self, mgs_local_info):
        try:
            mgs = ManagementTarget.objects.get(targetmount__host = self.host)
        except ManagementTarget.DoesNotExist:
            # FIXME: when there is no LNet info for self.host, we cannot be 
            # sure if this is a new MGS or a failover for an existing one
            existing_mgs = None
            for mgs in ManagementTarget.objects.all():
                if mgs_local_info['params'].has_key('failover.node'):
                    failovers = set(normalize_nids(AuditTarget.target_param(mgs, 'failover.node')))
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
                tm,created = TargetMount.objects.get_or_create(target = mgs, host = self.host, primary = primary, mount_point = mgs_local_info['mount_point'], block_device = mgs_local_info['device'])
                if created:
                    log().info("Learned MGS mount on %s" % self.host)
                    self.learn_event(tm)
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
        for mgs in ManagementTarget.objects.all():
            mgs_host_nids = set()
            mgs_hosts = set()
            for mgs_mount in mgs.targetmount_set.all():
                mgs_host = mgs_mount.host
                mgs_host_nids |= set(normalize_nids([n.nid_string for n in mgs_host.nid_set.all()]))
                mgs_hosts |= set([mgs_host])

            if len(mgs_host_nids) == 0:
                log().warning("mgs = %s %d, mounts=%s" % (mgs, mgs.id, mgs.targetmount_set.all()))
                log().warning("Cannot map targets on MGS to local locations because MGS nids are not yet known -- LNet is probably down on the MGS?")
                continue

            for local_info in self.host_data['local_targets']:
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

                # See if this target is using the mgs 'mgs'
                mgs_match = False
                if tgt_mgs_nids == set(["0@lo"]) or len(tgt_mgs_nids) == 0:
                    # An empty nid list or 0@lo indicates a local mgs, match 
                    # an MGS if the local host is in the set of hosts on which
                    # this MGS is mounted
                    if self.host in mgs_hosts:
                        mgs_match = True
                elif tgt_mgs_nids & mgs_host_nids:
                    # Otherwise, match an MGS if there is overlap between the 
                    # NIDs of hosts where the MGS is mounted, and the MGS NIDs
                    # used by this local target.
                    mgs_match = True

                if not mgs_match:
                    continue
    
                # TODO: detect case where we find a targetmount that matches one 
                # which already exists for a different target, where the other target
                # has no name -- in this case we are overlapping with a blank target
                # that was created during configuration.

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
                    (tm, created) = TargetMount.objects.get_or_create(target = matched_target,
                            host = self.host, primary = primary,
                            mount_point = local_info['mount_point'],
                            block_device = local_info['device'])
                    if created:
                        log().info("Learned association %d between %s and host %s" % (tm.id, local_info['name'], self.host))
                        self.learn_event(tm)
                except NoLNetInfo:
                    log().warning("Cannot set up target %s on %s until LNet is running" % (local_info['name'], self.address))

    def learn_mgs_targets(self, filesystem_targets):
        # Learn any targets
        for fs, targets in filesystem_targets.items():
            for target in targets:
                name = target['name']

                if name.find("-MDT") != -1:
                    klass = MetadataTarget
                elif name.find("-OST") != -1:
                    klass = ObjectStoreTarget

                (target, created) = klass.objects.get_or_create(
                    name = name, filesystem = fs)
                if created:
                    log().info("Learned %s %s" % (klass.__name__, name))
                    self.learn_event(target)

    def learn_event(self, learned_item):
        from logging import INFO
        LearnEvent(severity = INFO, host = self.host, learned_item = learned_item).save()

    def learn_target_states(self):
        for mount_info in self.host_data['local_targets']:
            if mount_info['kind'] == 'MGS':
                target = ManagementTarget.get_by_host(self.host)
                mountable = target.targetmount_set.get(host = self.host, mount_point = mount_info['mount_point'])
                
                MountableOfflineAlert.notify(mountable, not mount_info['running'])
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

                    if target_val.filesystem.mgs == mgs:
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

                MountableOfflineAlert.notify(mountable, not mount_info['running'])
                TargetRecoveryAlert.notify(mountable, audit_mountable.is_recovering())

            audit_mountable.save()
            # Fill out an AuditTarget object as well, potentially multiple times if
            # we encounter the target on multiple hosts
            audit_target,created = self.audit.audittarget_set.get_or_create(
                    target = mountable.target, audit = self.audit)
            if created:
                for key, val_list in mount_info['params'].items():
                    for val in val_list:
                        audit_target.auditparam_set.get_or_create(key = key, value = val)

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

        # Learn any targets from within this MGS
        self.learn_mgs_targets(filesystem_targets)

