#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


"""Plugin authors are encouraged to inherit from these classes when there is
a clear analogy between an object in their plugin and one of those provided here.

"""

from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource, BaseScannableResource
from chroma_core.lib.storage_plugin.api import attributes


class Resource(BaseStorageResource):
    pass


class ScannableResource(BaseStorageResource, BaseScannableResource):
    pass


class Host(BaseStorageResource):
    class Meta:
        label = 'Host'
        icon = 'host'


class PathWeight(BaseStorageResource):
    weight = attributes.Integer()


class LogicalDriveOccupier(BaseStorageResource):
    """When a subclass of this class is the descendent of a LogicalDrive, that LogicalDrive
    is considered unavailable.  This is used for marking LUNs/partitions/LVs which are
    in use, for example those which are mounted in existing file systems."""
    pass


class VirtualMachine(BaseStorageResource):
    """A Linux* host provided by a plugin.  This resource has a special behaviour when
    created: the manager server will add this (by the ``address`` attribute) as a Lustre server and
    attempt to configure the ``chroma-agent`` service on it.  The ``host_id`` attribute is used internally
    by the manager server and must not be assigned to by plugins."""
    # NB address is used to cue the creation of a ManagedHost, once that is set up
    # this address is not used.
    address = attributes.String()

    host_id = attributes.Integer(optional = True)


class DeviceNode(BaseStorageResource):
    host_id = attributes.Integer()
    path = attributes.PosixPath()
    logical_drive = attributes.ResourceReference(optional = True)

    class Meta:
        label = 'Device node'

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
    """A storage device with a fixed size that could be used for installing the Lustre software"""
    class Meta:
        icon = 'virtual_disk'

    size = attributes.Bytes()
    filesystem_type = attributes.Boolean(optional=True)

    """ This has to be a class method today because at the point we call it we only has the type not the object"""
    @classmethod
    def device_type(cls):
        """ By default devices are linux block devices """
        return "linux"


class LogicalDriveSlice(LogicalDrive):
    """A part of a slicable device like partition or lvm"""
    pass


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
    class Meta:
        label = 'Storage pool'
        icon = 'storage_pool'


class PhysicalDisk(BaseStorageResource):
    """A physical storage device, such as a hard drive or SSD"""
    class Meta:
        label = 'Physical disk'
        icon = 'physical_disk'


class NetworkInterface(BaseStorageResource):
    host_id = attributes.Integer()

    class Meta:
        label = 'Network node'


class LNETInterface(BaseStorageResource):

    class Meta:
        label = 'LNET Interface'


class LNETModules(BaseStorageResource):
    host_id = attributes.Integer()

    class Meta:
        label = 'LNET State'
