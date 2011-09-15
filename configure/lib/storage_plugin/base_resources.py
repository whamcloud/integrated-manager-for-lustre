
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.storage_plugin.resource import VendorResource
from configure.lib.storage_plugin import attributes

class PhysicalDisk(VendorResource):
    pass

class VirtualDisk(VendorResource):
    pass

class Controller(VendorResource):
    pass

class Fan(VendorResource):
    pass

class Enclosure(VendorResource):
    pass

class DeviceNode(VendorResource):
    host = attributes.HostName()
    path = attributes.PosixPath()

