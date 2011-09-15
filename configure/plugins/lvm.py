
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.storage_plugin import VendorResource, VendorPlugin, ResourceNotFound
from configure.lib.storage_plugin import LocalId, GlobalId
from configure.lib.storage_plugin import ResourceAttribute

from configure.lib.storage_plugin import attributes

class LvmPlugin(VendorPlugin):
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

    def initial_scan(self):
        # Get the list of user-configured hosts to scan
        root_resources = self.get_root_resources()
        for lvm_host_resource in root_resources:
            assert(isinstance(lvm_host_resource, LvmHost))
            hostname = lvm_host_resource.hostname
            code, out, err = self.simple_ssh(hostname, "vgs --units b --noheadings -o vg_name,vg_uuid,vg_size")
            if code != 0:
                self.log.error("Bad code %s from SSH call: %s %s" %(code, out, err))
                raise RuntimeError()

            vol_group_resources = []
            lines = [l for l in out.split("\n") if len(l) > 0]
            for line in lines:
                name, uuid, size_str = line.split()
                size = int(size_str[0:-1], 10)
                self.log.info("Learned VG %s %s %s" % (name, uuid, size))
                group = LvmGroup(uuid = uuid, name = name, size = size)
                group.add_parent(lvm_host_resource)
                self.register_resource(group)
                vol_group_resources.append(group)

            for vgr in vol_group_resources:
                code, out, err = self.simple_ssh(hostname, "lvs --units b --noheadings -o lv_name,lv_uuid,lv_size,lv_path %s" % vgr.name)
                if code != 0:
                    self.log.error("Bad code %s from lvs call for %s: %s %s" % (code, vgr.name, out, err))
                    raise RuntimeError()

                lines = [l for l in out.split("\n") if len(l) > 0]
                for line in lines:
                    name, uuid, size_str, path = line.split()
                    size = int(size_str[0:-1], 10)
                    self.log.info("Learned LV %s %s %s" % (name, uuid, size))
                    vol = LvmVolume(uuid = uuid, name = name, size = size)
                    vol.add_parent(vgr)
                    self.register_resource(vol)
                    node = LvmDeviceNode(host = lvm_host_resource.hostname, path = path)
                    node.add_parent(vol)
                    self.register_resource(node)

    def update_scan(self):
        # Get the list of user-configured hosts to scan
        root_resources = self.get_root_resources()

        for lvm_host_resource in root_resources:
            hostname = lvm_host_resource.hostname
            code, out, err = self.simple_ssh(hostname, "vgs --units b --noheadings -o vg_name,vg_uuid,vg_size")
            if code != 0:
                self.log.error("Bad code %s from SSH call: %s %s" %(code, out, err))
                raise RuntimeError()

            vol_group_resources = []
            lines = [l for l in out.split("\n") if len(l) > 0]
            found_groups = set()
            for line in lines:
                name, uuid, size_str = line.split()
                size = int(size_str[0:-1], 10)
                found_groups.add(uuid)
                try:
                    group_resource = self.lookup_global_resource(LvmGroup, uuid = uuid, name = name, size = size)
                    group_resource.name = name
                    group_resource.size = size
                except ResourceNotFound:
                    group = LvmGroup(uuid = uuid, name = name, size = size)
                    group.add_parent(lvm_host_resource)
                    self.register_resource(group)

            for vg in self.lookup_children(lvm_host_resource, LvmGroup):
                if not vg.uuid in found_groups:
                    self.deregister_resource(vg)
                code, out, err = self.simple_ssh(hostname, "lvs --units b --noheadings -o lv_name,lv_uuid,lv_size,lv_path %s" % vg.name)
                if code != 0:
                    self.log.error("Bad code %s from lvs call for %s: %s %s" % (code, vgr.name, out, err))
                    raise RuntimeError()

                lines = [l for l in out.split("\n") if len(l) > 0]
                found_vols = set()
                for line in lines:
                    name, uuid, size_str, path = line.split()
                    size = int(size_str[0:-1], 10)
                    found_vols.add(name)
                    try:
                        vol_resource = self.lookup_local_resource(vg, LvmVolume, uuid = uuid, name = name, size = size)
                        vol_resource.name = name
                        vol_resource.size = size
                    except ResourceNotFound:
                        vol = LvmVolume(uuid = uuid, name = name, size = size)
                        vol.add_parent(vg)
                        self.register_resource(vol)
                        node = LvmDeviceNode(host = lvm_host_resource.hostname, path = path)
                        node.add_parent(vol)
                        self.register_resource(node)

                for lv in self.lookup_children(vg, LvmVolume):
                    if not lv.name in found_vols:
                        self.deregister_resource(lv)

class LvmGroup(VendorResource):
    identifier = GlobalId('uuid')

    uuid = attributes.Uuid()
    name = attributes.String()
    size = attributes.Bytes()

class LvmVolume(VendorResource):
    # LVM Volumes actually have a UUID but we're using a LocalId to 
    # exercise the code path
    identifier = LocalId(LvmGroup, 'name')
    
    uuid = attributes.Uuid()
    name = attributes.String()
    size = attributes.Bytes()

from configure.lib.storage_plugin import base_resources
class LvmDeviceNode(base_resources.DeviceNode):
    identifier = GlobalId('host', 'path')
    # Just using the built in HostName and PosixPath from DeviceNode
    pass

class LvmHost(VendorResource):    
    """A host on which we wish to identify LVM managed storage.
       Assumed to be accessible by passwordless SSH as the hydra
       user: XXX NOT WRITTEN FOR PRODUCTION USE"""
    identifier = GlobalId('hostname')
    hostname = ResourceAttribute() 

