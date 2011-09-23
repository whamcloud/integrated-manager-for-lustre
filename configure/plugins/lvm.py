
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.storage_plugin import VendorResource, VendorPlugin, ResourceNotFound
from configure.lib.storage_plugin import LocalId, GlobalId
from configure.lib.storage_plugin import ResourceAttribute

from configure.lib.storage_plugin import attributes
from configure.lib.storage_plugin import base_resources

class LvmPlugin(VendorPlugin):
    def initial_scan(self):
        # Get the list of user-configured hosts to scan
        root_resources = self.get_root_resources()
        for lvm_host_resource in root_resources:
            assert(isinstance(lvm_host_resource, LvmHost))
            hostname = lvm_host_resource.hostname

            vol_group_resources = []
            for name, uuid, size in LvmScanner(self.log).get_vgs(hostname):
                self.log.info("Learned VG %s %s %s" % (name, uuid, size))
                group, created = self.update_or_create(LvmGroup, parents=[lvm_host_resource],
                        uuid = uuid, name = name, size = size)
                vol_group_resources.append(group)

            for vgr in vol_group_resources:
                for name, uuid, size, path in LvmScanner(self.log).get_lvs(hostname, vgr.name):
                    self.log.info("Learned LV %s %s %s" % (name, uuid, size))
                    vol,created = self.update_or_create(LvmVolume, parents = [vgr],
                            uuid = uuid, name = name, size = size)
                    node,created = self.update_or_create(LvmDeviceNode, parents = [vol],
                            host = lvm_host_resource.hostname, path = path)

    def update_scan(self):
        # Get the list of user-configured hosts to scan
        root_resources = self.get_root_resources()

        for lvm_host_resource in root_resources:
            hostname = lvm_host_resource.hostname

            # Update or add VGs
            found_groups = set()
            for name, uuid, size in LvmScanner(self.log).get_vgs(hostname):
                found_groups.add(uuid)
                resource,created = self.update_or_create(LvmGroup, parents=[lvm_host_resource],
                        uuid = uuid, name = name, size = size)

            # Deregister any previously-registered VGs which were not found on this scan
            for vg in self.lookup_children(lvm_host_resource, LvmGroup):
                if not vg.uuid in found_groups:
                    self.deregister_resource(vg)

            found_vols = set()
            for vg in self.lookup_children(lvm_host_resource, LvmGroup):
                # Update or add LVs
                for name, uuid, size, path in LvmScanner(self.log).get_lvs(hostname, vg.name):
                    found_vols.add(name)
                    vol, created = self.update_or_create(LvmVolume, parents=[vg], uuid = uuid, name = name, size = size)
                    node, created = self.update_or_create(LvmDeviceNode, parents=[vol], host = lvm_host_resource.hostname, path = path)

                # Deregister any previously-registered LVs which were not found on this scan
                for lv in self.lookup_children(vg, LvmVolume):
                    if not lv.name in found_vols:
                        self.deregister_resource(lv)

class LvmScanner(object):
    """This module is independent of hydra's plugin framework and provides an
    example of an existing library to access storage information"""

    def __init__(self, log):
        self.log = log

    def simple_ssh(self, hostname, command):
        """Like configure.lib.job.debug_ssh but doesn't require a Host instance"""
        import paramiko
        import socket
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # How long it may take to establish a TCP connection
        SOCKET_TIMEOUT = 3600
        # How long it may take to get the output of our agent
        # (including tunefs'ing N devices)
        SSH_READ_TIMEOUT = 3600

        args = {"hostname": hostname,
                "username": 'root',
                "timeout": SOCKET_TIMEOUT}
        ssh.connect(**args)
        transport = ssh.get_transport()
        channel = transport.open_session()
        channel.settimeout(SSH_READ_TIMEOUT)
        channel.exec_command(command)
        result_stdout = channel.makefile('rb').read()
        result_stderr = channel.makefile_stderr('rb').read()
        result_code = channel.recv_exit_status()
        ssh.close()

        self.log.debug("simple_ssh:%s:%s:%s" % (hostname, result_code, command))
        if result_code != 0:
            self.log.error("simple_ssh:%s:%s:%s" % (hostname, result_code, command))
            self.log.error(result_stdout)
            self.log.error(result_stderr)
        return result_code, result_stdout, result_stderr

    def get_vgs(self, hostname):
        code, out, err = self.simple_ssh(hostname, "vgs --units b --noheadings -o vg_name,vg_uuid,vg_size")
        if code != 0:
            self.log.error("Bad code %s from SSH call: %s %s" % (code, out, err))
            raise RuntimeError()

        vol_group_resources = []
        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            name, uuid, size_str = line.split()
            size = int(size_str[0:-1], 10)
            yield (name, uuid, size)

    def get_lvs(self, hostname, vg_name):
        code, out, err = self.simple_ssh(hostname, "lvs --units b --noheadings -o lv_name,lv_uuid,lv_size,lv_path %s" % vg_name)
        if code != 0:
            self.log.error("Bad code %s from lvs call for %s: %s %s" % (code, vg_name, out, err))
            raise RuntimeError()

        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            name, uuid, size_str, path = line.split()
            size = int(size_str[0:-1], 10)
            yield (name, uuid, size, path)

class LvmGroup(base_resources.StoragePool):
    identifier = GlobalId('uuid')

    uuid = attributes.Uuid()
    name = attributes.String()
    size = attributes.Bytes()

    icon = 'lvm_vg'
    human_name = 'VG'

    def human_string(self, parent = None):
        return self.name

class LvmVolume(base_resources.VirtualDisk):
    # LVM Volumes actually have a UUID but we're using a LocalId to 
    # exercise the code path
    identifier = LocalId(LvmGroup, 'name')
    
    uuid = attributes.Uuid()
    name = attributes.String()
    size = attributes.Bytes()

    icon = 'lvm_lv'
    human_name = 'LV'

    def human_string(self, ancestors = []):
        if LvmGroup in [a.__class__ for a in ancestors]:
            return self.name
        else:
            group = self.get_parent(LvmGroup) 
            return "%s-%s" % (group.name, self.name)

class LvmDeviceNode(base_resources.DeviceNode):
    identifier = GlobalId('host', 'path')
    # Just using the built in HostName and PosixPath from DeviceNode
    def human_string(self, ancestors = []):
        ancestor_klasses = dict([(i.__class__, i) for i in ancestors])
        if LvmHost in ancestor_klasses and LvmVolume in ancestor_klasses:
            # Host .. Volume .. me
            # I'm just my path
            return self.path
        else:
            # Volume .. me
            # or just 'me'
            # I'm my host and my path
            return "%s: %s" % (self.host, self.path)


class LvmHost(base_resources.Host):    
    """A host on which we wish to identify LVM managed storage.
       Assumed to be accessible by passwordless SSH as the hydra
       user: XXX NOT WRITTEN FOR PRODUCTION USE"""
    identifier = GlobalId('hostname')
    hostname = ResourceAttribute() 

    def human_string(self, ancestors = []):
        return self.hostname

