#!/usr/bin/env python
from django.core.management import setup_environ
import settings
setup_environ(settings)

# Access to 'monitor' database
from monitor.models import *

# Using clustershell
from ClusterShell.Task import task_self, NodeSet

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

def is_primary(host, local_target_info):
    local_nids = [n.nid_string for n in host.nid_set.all()]

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

class LustreAudit:
    def __init__(self):
        self.raw_data = None
        self.target_locations = None
        self.audit = None
    
    def audit_all(self):
        hosts = Host.objects.all()
        self.audit_hosts(hosts)

    def audit_host(self, host):
        audit = self.audit_hosts([host], learn_state = False)
        if audit.audithost_set.count() == 0:
            raise HostAuditError(host)

    def nids_to_mgs(self, nid_strings):
        nids = Nid.objects.filter(nid_string__in = nid_strings)
        hosts = set([n.host for n in nids])
        # TODO: detect and report the pathological case where someone has given
        # us two NIDs that refer to different hosts which both have a 
        # targetmount for a ManagementTarget, but they're not the
        # same ManagementTarget.
        for h in hosts:
            for target_mount in h.targetmount_set.all():
                target = target_mount.target.downcast()
                if isinstance(target, ManagementTarget):
                    return target
        
        raise ManagementTarget.DoesNotExist

    def audit_hosts(self, hosts):
        if len(hosts) == 0:
            return

        # Record start of audit
        self.audit = Audit(complete=False)
        self.audit.save()
        for h in hosts:
            self.audit.attempted_hosts.add(h)

        # Invoke hydra-agent
        self.raw_data = self.get_raw_data(hosts)

        # Update the Nids associated with each Host
        self.learn_nids()

        # Build a temporary map of where named targets were found on hosts
        self.target_locations = self.get_target_locations()

        # Create Filesystem, Target and TargetMount objects
        self.learn_fs_targets()

        # Set 'mounted' status on Target objects
        self.learn_target_states()

        # Create and get state of Client objects
        self.learn_clients()

        self.audit.complete = True
        self.audit.save()

        return self.audit

    def learn_nids(self):
        for audit_host, data in self.raw_data.items():
            host = audit_host.host
            new_host_nids = set(normalize_nids(data['lnet_nids']))
            old_host_nids = set([n.nid_string for n in host.nid_set.all()])
            create_nids = new_host_nids - old_host_nids
            for n in create_nids:
                host.nid_set.create(nid_string = n)
            if len(new_host_nids) > 0:
                delete_nids = old_host_nids - new_host_nids
                host.nid_set.filter(nid_string = delete_nids).delete()

            for nid_str in new_host_nids:
                audit_host.auditnid_set.create(nid_string = nid_str)

    def get_target_locations(self):
        """Return map of (target name, [mgs_nid,]) to (host, mount_info)"""
        target_locations = defaultdict(list)

        for audit_host, data in self.raw_data.items():
            for mount_info in data['local_targets']:
                tgt_mgs_nids = []
                try:
                    # NB I'm not sure whether tunefs.lustre will give me 
                    # one comma-separated mgsnode, or a series of mgsnode
                    # settings, so handle both
                    for n in mount_info['params']['mgsnode']:
                        tgt_mgs_nids.extend(n.split(","))
                except KeyError:
                    # 'mgsnode' doesn't have to be present
                    pass
                tgt_mgs_nids = tuple(normalize_nids(tgt_mgs_nids))

                target_locations[(mount_info['name'], tgt_mgs_nids)].append(
                        (audit_host.host, normalize_nids(data['lnet_nids']), mount_info))

        return target_locations

    def learn_mgs(self, host, data):
        try:
            mgs = ManagementTarget.get_by_host(host)
        except ManagementTarget.DoesNotExist:
            # This can either be a newly discovered MGS, or it could be an existing
            # MGS 
            mgs = ManagementTarget(name = "MGS")
            mgs.save()
            log().info("Learned MGS on %s" % host)
            # Find the local_targets info for the MGS
            #  * if it has no failnode, then this is definitely primary (+ if
            #    it's configured on more than one host then that's an error)
            #  * if it has one or more failnodes, then this is the primary if 
            #    none of the failnode NIDs match a local NID of this host.

            mgs_local_info = None
            for target in data['local_targets']:
                if target['kind'] == 'MGS':
                    mgs_local_info = target
            if mgs_local_info == None:
                raise RuntimeError("Got mgs_targets but no MGS local_target!")
            
            try:
                primary = is_primary(host, mgs_local_info)
                tm = TargetMount(target = mgs, host = host, primary = primary, mount_point = mgs_local_info['mount_point'], block_device = mgs_local_info['device'])
                tm.save()
            except NoLNetInfo:
                log().warning("Cannot fully set up MGS on %s until LNet is running")

        return mgs

    def learn_mgs_targets(self, filesystem_targets, mgs_host_nids):
        # Learn any targets
        for fs, targets in filesystem_targets.items():
            for target in targets:
                name = target['name']

                # Resolve name + nids of this mgs to locations for this target
                for nid in mgs_host_nids:
                    local_info = None
                    for ((name_val, mgs_nids_val), info_val) in self.target_locations.items():
                        if name_val == name and nid in mgs_nids_val:
                            local_info = info_val
                            break

                if local_info == None:
                    log().warning("Target %s found on MGS but not locally on any audited hosts" % (name))
                    continue
                else:
                    for (host, location_nids, local_target) in local_info:
                        if name.find("-MDT") != -1:
                            klass = MetadataTarget
                        elif name.find("-OST") != -1:
                            klass = ObjectStoreTarget

                    
                        try:
                            # See if there's a new unnamed target that we can fill out 
                            # the name for
                            target = klass.objects.get(targetmount__host = host,
                                    targetmount__mount_point = local_target['mount_point'],
                                    targetmount__block_device = local_target['device'],
                                    filesystem = fs,
                                    name = None)
                            target.name = local_target['name']
                            target.save()
                            log().info("Learned name '%s' for %s on %s" % (
                                local_target['name'], local_target['device'], host.address))
                        except klass.DoesNotExist:
                            (target, created) = klass.objects.get_or_create(
                                name = local_target['name'], filesystem = fs)
                            if created:
                                log().info("Learned %s %s" % (klass.__name__, name))

                        try:
                            primary = is_primary(host, local_target)
                            (tm, created) = TargetMount.objects.get_or_create(target = target,
                                    host = host, primary = primary,
                                    mount_point = local_target['mount_point'],
                                    block_device = local_target['device'])
                            if created:
                                log().info("Learned association %d between %s and host %s" % (tm.id, name, host.address))
                        except NoLNetInfo:
                            log().warning("Cannot set up target %s on %s until LNet is running" % (name, host.address))

    def learn_target_states(self):
        for audit_host, data in self.raw_data.items():
            for mount_info in data['local_targets']:
                if mount_info['kind'] == 'MGS':
                    target = ManagementTarget.get_by_host(audit_host.host)
                    mountable = target.targetmount_set.get(host = audit_host.host, mount_point = mount_info['mount_point'])

                    audit_mountable = AuditMountable(audit = self.audit,
                            mountable = mountable, mounted = mount_info['running'])
                else:
                    # Find the MGS based on mount_info['params']['mgsnode']
                    mgsnode_nids = normalize_nids(mount_info['params']['mgsnode'][0].split(","))
                    try:
                        mgs = self.nids_to_mgs(mgsnode_nids)
                    except ManagementTarget.DoesNotExist:
                        log().warning("Cannot find MGS for target %s (nids %s) on host %s" % (mount_info['name'], mgsnode_nids, audit_host.host.address))
                        continue

                    mountable = None
                    for target_val in Target.objects.filter(name = mount_info['name']):
                        target_val = target_val.downcast()
                        if not isinstance(target_val, FilesystemMember):
                            continue

                        if target_val.filesystem.mgs == mgs:
                            mountable = target_val.targetmount_set.get(host = audit_host.host,
                                            mount_point = mount_info['mount_point'])
                            break

                    if mountable == None:
                        log().warning("Cannot find target %s for mgs nids %s" % (mount_info['name'], mgsnode_nids))
                        continue

                    audit_mountable = AuditRecoverable(audit = self.audit, 
                            mountable = mountable, mounted = mount_info['running'],
                            recovery_status = json.dumps(mount_info["recovery_status"]))

                audit_target,created = self.audit.audittarget_set.get_or_create(target = mountable.target, audit = self.audit)
                if created:
                    for key, val_list in mount_info['params'].items():
                        for val in val_list:
                            audit_target.auditparam_set.create(key = key, value = val)

                audit_mountable.save()

    def learn_clients(self):
        for audit_host, data in self.raw_data.items():
            for mount_point, client_info in data['client_mounts'].items():
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
                    log().warning("Ignoring client mount for unknown filesystem '%s' on %s" % (client_info['filesystem'], audit_host.host))
                    continue

                # Instantiate Client
                (client, created) = Client.objects.get_or_create(
                        host = audit_host.host, mount_point = mount_point, filesystem = fs)
                if created:
                    log().info("Learned client %s" % client)

                audit_mountable = AuditMountable(audit = self.audit, mountable = client, mounted = client_info['mounted'])
                audit_mountable.save()

    def learn_fs_targets(self):
        for audit_host, data in self.raw_data.items():
            found_mgs = False
            for volume in data['local_targets']:
                if volume['kind'] == "MGS":
                    found_mgs = True
            if not found_mgs:
                continue

            # Learn an MGS target and a TargetMount for this host
            mgs = self.learn_mgs(audit_host.host, data)

            # Create Filesystem objects for all those in this MGS
            filesystem_targets = {}
            for fs_name, targets in data['mgs_targets'].items():
                (fs, created) = Filesystem.objects.get_or_create(name = fs_name, mgs = mgs)
                if created:
                    log().info("Learned filesystem '%s'" % fs_name)
                filesystem_targets[fs] = targets

            self.learn_mgs_targets(filesystem_targets, normalize_nids(data['lnet_nids']))

    def get_raw_data(self, hosts):
        # Invoke hydra-agent remotely
        # ===========================
        addresses = [str(h.address) for h in hosts]
        log().info("Auditing hosts: %s" % ", ".join(addresses))
        task = task_self()
        task.shell(AGENT_PATH, nodes = NodeSet.fromlist(addresses))
        task.resume()

        # Map of ManagementTarget to list of nids
        mgs_nids = defaultdict(list)

        # Map of AuditHost to output of hydra-agent
        raw_data = {}
        for output, nodes in task.iter_buffers():
            for node in nodes:
                log().info("Parsing JSON from %s" % str(node))
                output = "%s" % output
                try:
                    data = json.loads(output)
                except Exception,e:
                    log().error("bad output from %s: %s '%s'" % (str(node), e, output))
                    continue
            
                host = Host.objects.get(address = node)
                audit_host = AuditHost(audit = self.audit, host = host, lnet_up = data['lnet_up'])
                audit_host.save()

                raw_data[audit_host] = data

        return raw_data

