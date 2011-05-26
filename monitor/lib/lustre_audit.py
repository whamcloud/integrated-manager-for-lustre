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

from logging import getLogger, FileHandler, INFO
getLogger(__name__).setLevel(INFO)
getLogger(__name__).addHandler(FileHandler("%s.log" % __name__))
def log():
    return getLogger(__name__)

class HostAuditError(Exception):
    def __init__(self, host, *args, **kwargs):
        self.host = host
        super(HostAuditError, self).__init__(*args, **kwargs)

class LustreAudit:
    def __init__(self):
        self.issues = []
    
    def audit_all(self):
        hosts = Host.objects.all()
        self.audit_hosts(hosts)

    def audit_host(self, host):
        audit = self.audit_hosts([host], learn_state = False)
        if audit.audithost_set.count() == 0:
            raise HostAuditError(host)

    def audit_hosts(self, hosts):
        addresses = [str(h.address) for h in hosts]
        log().info("Auditing hosts: %s" % ", ".join(addresses))
        task = task_self()
        task.shell("/root/wche_audit.py", nodes = NodeSet.fromlist(addresses))
        task.resume()

        targets = {}
        mgs_targets = {}
        mgs_pings = {}

        audit = Audit(complete=False)
        audit.save()
        for h in hosts:
            audit.attempted_hosts.add(h)

        # Map of AuditHost to dict
        audit_data = {}

        # First pass: create AuditHosts and store state dicts
        # ===================================================
        for output, nodes in task.iter_buffers():
            for node in nodes:
                log().info(str(node))
                log().info("=" * len(str(node)))
                output = "%s" % output
                try:
                    data = json.loads(output)
                except Exception,e:
                    log().error("bad output from %s: %s '%s'" % (node, e, output))
                    print "bad output from %s: %s '%s'" % (node, e, output)
                    continue
            
                host = Host.objects.get(address = node)
                audit_host = AuditHost(audit = audit, host = host, lnet_up = data['lnet_up'])
                audit_host.save()
                for nid_str in data['lnet_nids']:
                    audit_host.auditnid_set.create(nid_string = nid_str)

                audit_data[audit_host] = data
        
        # Second pass: try to learn any unknown filesystems, targets
        # =========================================================
        for audit_host, data in audit_data.items():
            if len(data['mgs_targets']) > 0:
                # List of filesystems on this mgs
                filesystem_targets = {}
                for fs_name, targets in data['mgs_targets'].items():
                    (fs, created) = Filesystem.objects.get_or_create(name = fs_name)
                    if created:
                        log().info("Learned filesystem '%s'" % fs_name)
                    filesystem_targets[fs] = targets

                # FIXME: what's with name always being "MGS"?  Does it mean anything?
                (mgs, created) = ManagementTarget.objects.get_or_create(host = audit_host.host, name = "MGS")
                if created:
                    log().info("Learned MGS on %s" % audit_host.host)

                for fs in filesystem_targets.keys():
                    # .add does not duplicate if fs is already there
                    mgs.filesystems.add(fs)

                # Learn any targets
                for fs, targets in filesystem_targets.items():
                    for target in targets:
                        name = target['name']
                        if name.find("-MDT") != -1:
                            (mdt, created) = MetadataTarget.objects.get_or_create(name = target['name'], host = audit_host.host, filesystem = fs)
                            if created:
                                log().info("Learned MDT %s" % name)
                        elif name.find("-OST") != -1:
                            (ost, created) = ObjectStoreTarget.objects.get_or_create(name = target['name'], host = audit_host.host, filesystem = fs)
                            if created:
                                log().info("Learned OST %s" % name)
                    
       
        # Third pass: learn client and target states
        # ===================================================
        for audit_host, data in audit_data.items():
            for fs_name, mount_info in data['client_mounts'].items():
                try:
                    fs = Filesystem.objects.get(name = fs_name)
                except Filesystem.DoesNotExist:
                    log().warning("Ignoring client mount for unknown filesystem '%s' on %s" % (fs_name, audit_host.host))
                    continue
                (client, created) = Client.objects.get_or_create(host = audit_host.host, mount_point = mount_info['mount_point'], filesystem = fs)
                if created:
                    log().info("Learned client %s" % client)

                audit_mountable = AuditMountable(audit = audit, audit_host = audit_host, mountable = client, mounted = mount_info['mounted'])
                audit_mountable.save()

            for mount_info in data['local_targets']:
                try:
                    # FIXME: don't require specific host unless talking about 
                    # an MGS (which won't have unique name)
                    local_mountable = LocalMountable.objects.get(name = mount_info['name'], host = audit_host.host)
                except LocalMountable.DoesNotExist:
                    log().warning("Unknown target %s on host %s" % (mount_info['name'], audit_host.host))
                    continue
                
                if mount_info['kind'] != "MGS":
                    audit_mountable = AuditRecoverable(audit = audit, audit_host = audit_host, mountable = local_mountable, mounted = mount_info['running'], recovery_status = json.dumps(mount_info["recovery_status"]))
                else:
                    audit_mountable = AuditMountable(audit = audit, audit_host = audit_host, mountable = local_mountable, mounted = mount_info['running'])
                audit_mountable.save()

        # Generate issues for any target which doesn't have an AuditMountable
        # Generate issues for any Target not found (unless the host where
        # we expected to find the target was not contacted)
        # Generate issues for any targets we found which do not correspond 
        # to any Target.
        audit.complete = True
        audit.save()

        return audit

    def print_latest_audit():
        audit = Audit.objects.filter(complete=True).latest("created_at")
        for target in audit.auditmountable_set.all():
            print target.target.name, target.mounted, target.recovery_status

if __name__ == '__main__':
    lustre_audit = LustreAudit()

    lustre_audit.audit_all(discover)
    lustre_audit.print_latest_audit()

