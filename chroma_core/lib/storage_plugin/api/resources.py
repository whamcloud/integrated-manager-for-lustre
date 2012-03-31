
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource, ScannableResource
from chroma_core.lib.storage_plugin.api import attributes


class Resource(BaseStorageResource):
    pass


class ScannableResource(BaseStorageResource, ScannableResource):
    pass


class Host(BaseStorageResource):
    class_label = 'Host'
    icon = 'host'


class PathWeight(BaseStorageResource):
    weight = attributes.Integer()


class VirtualMachine(BaseStorageResource):
    """A linux host provided by a plugin.  This resource has a special behaviour when
    created: Chroma will add this (by the ``address`` attribute) as a Lustre server and
    attempt to invoke the Chroma agent on it.  The ``host_id`` attribute is used internally
    by Chroma and must not be assigned to by plugins."""
    # NB address is used to cue the creation of a ManagedHost, once that is set up
    # this address is not used.
    address = attributes.String()

    host_id = attributes.Integer(optional = True)


class DeviceNode(BaseStorageResource):
    host_id = attributes.Integer()
    path = attributes.PosixPath()
    class_label = 'Device node'

    def get_label(self):
        path = self.path
        strip_strings = ["/dev/",
                         "/dev/mapper/",
                         "/dev/disk/by-id/",
                         "/dev/disk/by-path/"]
        strip_strings.sort(lambda a, b: cmp(len(b), len(a)))
        for s in strip_strings:
            if path.startswith(s):
                path = path[len(s):]
        return "%s:%s" % (self.host_id, path)


class LogicalDrive(BaseStorageResource):
    """A storage device with a fixed size that could be used for installing Lustre"""
    size = attributes.Bytes()
    icon = 'virtual_disk'


class Enclosure(BaseStorageResource):
    """A physical enclosure/drawer/shelf"""
    pass


class Fan(BaseStorageResource):
    """A physical cooling fan"""
    pass


class Controller(BaseStorageResource):
    """A RAID controller"""
    pass


class StoragePool(BaseStorageResource):
    """An aggregation of physical drives"""
    class_label = 'Storage pool'
    icon = 'storage_pool'


class PhysicalDisk(BaseStorageResource):
    """A physical storage device, such as a hard drive or SSD"""
    class_label = 'Physical disk'
    icon = 'physical_disk'
