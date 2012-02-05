
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.storage_plugin.resource import StorageResource
from configure.lib.storage_plugin import attributes


class Host(StorageResource):
    class_label = 'Host'
    icon = 'host'


class PhysicalDisk(StorageResource):
    """A physical storage device, such as a hard drive or SSD"""
    class_label = 'Physical disk'
    icon = 'physical_disk'


class VirtualDisk(StorageResource):
    """A storage device which will be presented to Linux servers.  Optionally set the ``home_controller``
    attribute to a resource representing a controller (half of a couplet) so that Chroma can infer
    which paths are the best for this device."""
    class_label = 'Virtual disk'
    icon = 'virtual_disk'
    home_controller = attributes.ResourceReference(optional = True)


class StoragePool(StorageResource):
    """An aggregation of physical drives"""
    class_label = 'Storage pool'
    icon = 'storage_pool'


class Controller(StorageResource):
    """A RAID controller"""
    pass


class Fan(StorageResource):
    """A physical cooling fan"""
    pass


class Enclosure(StorageResource):
    """A physical enclosure/drawer/shelf"""
    pass


class LogicalDrive(StorageResource):
    """A storage device with a fixed size that could be used for installing Lustre -- note that
    it is not typically necessary to use this class for LUNs on a storage controller as they are
    only treated as LogicalDrives once detected on a Linux server by Chroma"""
    size = attributes.Bytes()
    icon = 'virtual_disk'


class VirtualMachine(StorageResource):
    """A linux host provided by a plugin.  This resource has a special behaviour when
    created: Chroma will add this (by the ``address`` attribute) as a Lustre server and
    attempt to invoke the Chroma agent on it.  The ``host_id`` attribute is used internally
    by Chroma and must not be assigned to by plugins.  The ``home_controller`` attribute is
    used to indicate a storage controller whose LUNs are best accessed via this virtual
    machine -- see the ``VirtualDisk.home_controller``."""
    # NB address is used to cue the creation of a ManagedHost, once that is set up
    # this address is not used.
    address = attributes.String()

    home_controller = attributes.ResourceReference()
    host_id = attributes.Integer(optional = True)
