
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.storage_plugin.plugin import StoragePlugin
from configure.lib.storage_plugin.resource import StorageResource, ScannableId, GlobalId, ScannableResource

from configure.lib.storage_plugin import attributes
from configure.lib.storage_plugin import base_resources
from configure.lib.storage_plugin import alert_conditions

# This plugin is special, it uses Hydra's built-in infrastructure
# in a way that third party plugins can't/shouldn't/mustn't
from configure.lib.agent import Agent
from configure.models import ManagedHost

class HydraHostProxy(StorageResource, ScannableResource):
    identifier = GlobalId('host_id')

    host_id = attributes.Integer()
    def human_string(self, parent = None):
        host = ManagedHost._base_manager.get(pk=self.host_id)
        return "%s" % host

class BlockDevice(StorageResource):
    identifier = GlobalId('serial')

    serial = attributes.String()
    size = attributes.Bytes()

class DeviceNode(StorageResource):
    identifier = ScannableId('path')

    path = attributes.String()

class Linux(StoragePlugin):
    def __init__(self, *args, **kwargs):
        super(Linux, self).__init__(*args, **kwargs)
        self.agent = Agent(log = self.log)

    # TODO: need to document that initial_scan may not kick off async operations, because
    # the caller looks at overall resource state at exit of function.  If they eg
    # want to kick off an async update thread they should do it at the first
    # call to update_scan, or maybe we could give them a separate function for that.
    def initial_scan(self, root_resource):
        host = ManagedHost.objects.get(pk=root_resource.host_id)
        devices = self.agent.invoke(host, "device-scan")

        dm_block_devices = set()
        for vg, lv_list in devices['lvs'].items():
            for lv_name, lv in lv_list.items():
                dm_block_devices.add(lv['block_device'])
        for mp_name, mp in devices['mpath'].items(): 
            dm_block_devices.add(mp['block_device'])

        # List of BDs with serial numbers that aren't devicemapper BDs
        devs_by_serial = {}
        for bdev in devices['devs'].values():
            serial = bdev['serial']
            if serial != None and not bdev['major_minor'] in dm_block_devices and not serial in devs_by_serial:
                devs_by_serial[serial] = {
                        'serial': serial,
                        'size': bdev['size']
                        }

        # Resources for devices with serial numbers
        res_by_serial = {}
        for dev in devs_by_serial.values():
            res, created = self.update_or_create(BlockDevice, serial = dev['serial'], size = dev['size'])
            res_by_serial[dev['serial']] = res

        # Device nodes for devices with serial numbers                       
        for bdev in devices['devs'].values():
            if bdev['serial'] in devs_by_serial:
                lun_resource = res_by_serial[bdev['serial']]
                res, created = self.update_or_create(DeviceNode,
                                    parents = [lun_resource],
                                    path = bdev['path'])

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
    identifier = GlobalId('uuid')
    
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
    identifier = ScannableId('path')
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

class LinuxHost(base_resources.Host):    
    """A host on which we wish to identify LVM managed storage.
       Assumed to be accessible by passwordless SSH as the hydra
       user: XXX NOT WRITTEN FOR PRODUCTION USE"""
    identifier = GlobalId('hostname')
    hostname = attributes.String() 

    def human_string(self, ancestors = []):
        return self.hostname

