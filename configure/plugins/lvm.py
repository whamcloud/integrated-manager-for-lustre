
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.vendor_plugin import VendorResource, VendorPlugin
from configure.lib.vendor_plugin import LocalId, GlobalId
from configure.lib.vendor_plugin import ResourceAttribute

# Access to database makes this a server-only plugin
from configure.models import ManagedHost

class LvmPlugin(VendorPlugin):
    def initial_scan(self):
        # Get the list of user-configured hosts to scan
        root_resources = self.get_root_resources()
        for lvm_host_resource in root_resources:
            try:
                # XXX only mapping to ManagedHost for convenience of debug_ssh
                host = ManagedHost.objects.get(address = lvm_host_resource.hostname)
            except ManagedHost.DoesNotExist:
                self.log.error("No ManagedHost for LvmHost %s!" % ())
                continue

            from configure.lib.job import debug_ssh
            code, out, err = debug_ssh(host, "vgs --units b --noheadings -o vg_name,vg_uuid,vg_size")

            vol_group_resources = []

            if code == 0:
                try:
                    lines = out.split("\n")
                    for line in lines:
                        name, uuid, size_str = line.split()
                        size = int(size_str[0:-1], 10)
                        self.log.info("Learned VG %s %s %s" % (name, uuid, size))
                        group = LvmGroup(uuid = uuid, name = name, size = size)
                        group.add_parent(lvm_host_resource)
                        self.add_resource(group)
                        vol_group_resources.append(group)
                except ValueError:
                    pass
            else:
                self.log.error("Bad code %s from SSH call: %s %s" %(code, out, err))

            for vgr in vol_group_resources:
                code, out, err = debug_ssh(host, "lvs --units b --noheadings -o lv_name,lv_uuid,lv_size %s" % vgr.name)
                if code == 0:
                    lines = [l for l in out.split("\n") if len(l) > 0]
                    for line in lines:
                        name, uuid, size_str = line.split()
                        size = int(size_str[0:-1], 10)
                        self.log.info("Learned LV %s %s %s" % (name, uuid, size))
                        vol = LvmVolume(uuid = uuid, name = name, size = size)
                        vol.add_parent(vgr)
                        self.add_resource(vol)
                else:
                    self.log.error("Bad code %s from lvs call for %s: %s %s" % (code, vgr.name, out, err))

                
class LvmGroup(VendorResource):
    identifier = GlobalId('uuid')

    _fields = {
        'uuid': ResourceAttribute(),
        'name': ResourceAttribute(),
        'size': ResourceAttribute()
    }

class LvmVolume(VendorResource):
    # LVM Volumes actually have a UUID but we're using a LocalId to 
    # exercise the code path
    identifier = LocalId(LvmGroup, 'name')
    
    _fields = {
        'uuid': ResourceAttribute(),
        'name': ResourceAttribute(),
        'size': ResourceAttribute()
    }

class LvmHost(VendorResource):    
    """A host on which we wish to identify LVM managed storage.
       Assumed to be accessible by passwordless SSH as the hydra
       user: XXX NOT WRITTEN FOR PRODUCTION USE"""
    identifier = GlobalId('hostname')
    _fields = {
        'hostname': ResourceAttribute() 
    }

