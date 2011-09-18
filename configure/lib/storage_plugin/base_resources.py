
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.storage_plugin.resource import VendorResource
from configure.lib.storage_plugin import attributes

class Host(VendorResource):
    human_name = 'Host'
    icon = 'host'

class PhysicalDisk(VendorResource):
    human_name = 'Physical disk'
    icon = 'physical_disk'

class VirtualDisk(VendorResource):
    human_name = 'Virtual disk'
    icon = 'virtual_disk'

class StoragePool(VendorResource):
    human_name = 'Storage pool'
    icon = 'storage_pool'

class Controller(VendorResource):
    pass

class Fan(VendorResource):
    pass

class Enclosure(VendorResource):
    pass

class DeviceNode(VendorResource):
    host = attributes.HostName()
    path = attributes.PosixPath()

    human_name = 'Device node'

