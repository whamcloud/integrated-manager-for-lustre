# Copyright (c) 2018 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api import attributes

class ScsiDevice(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId('serial')
        label = "SCSI device"

    serial = attributes.String()

    def get_label(self):
        return self.serial


class UnsharedDevice(resources.LogicalDrive):
    class Meta:
        identifier = ScopedId('path')

    # Annoying duplication of this from the node, but it really
    # is the closest thing we have to a real ID.
    path = attributes.PosixPath()

    def get_label(self):
        hide_prefixes = ["/dev/disk/by-path/", "/dev/disk/by-id/"]
        path = self.path
        for prefix in hide_prefixes:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break

        return path


class LinuxDeviceNode(resources.DeviceNode):
    class Meta:
        identifier = ScopedId('path')


class Partition(resources.LogicalDriveSlice):
    class Meta:
        identifier = GlobalId('container', 'number')

    number = attributes.Integer()
    container = attributes.ResourceReference()

    def get_label(self):
        return "%s-%s" % (self.container.get_label(), self.number)


class MdRaid(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId('uuid')

    uuid = attributes.String()


class EMCPower(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId('uuid')

    uuid = attributes.String()


class ZfsPool(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId('uuid')

    uuid = attributes.String()
    name = attributes.String()
    """ This has to be a class method today because at the point we call it we only has the type not the object"""

    @classmethod
    def device_type(cls):
        return "zfs"

    def get_label(self):
        return self.name


class ZfsDataset(ZfsPool):
    class Meta:
        identifier = GlobalId('uuid')

    usable_for_lustre = False


class ZfsVol(ZfsPool):
    class Meta:
        identifier = GlobalId('uuid')


class ZfsPartition(Partition):
    class Meta:
        identifier = GlobalId('container', 'number')

    usable_for_lustre = False

class LocalMount(resources.LogicalDriveOccupier):
    """Used for marking devices which are already in use, so that
    we don't offer them for use as Lustre targets."""

    class Meta:
        identifier = ScopedId('mount_point')

    fstype = attributes.String()
    mount_point = attributes.String()


class LvmGroup(resources.StoragePool):
    class Meta:
        identifier = GlobalId('uuid')
        icon = 'lvm_vg'
        label = 'Volume group'

    uuid = attributes.Uuid()
    name = attributes.String()
    size = attributes.Bytes()

    def get_label(self):
        return self.name

class LvmVolume(resources.LogicalDriveSlice):
    # Q: Why is this identified by LV UUID and VG UUID rather than just
    #    LV UUID?  Isn't the LV UUID unique enough?
    # A: We're matching LVM2's behaviour.  If you e.g. imagine a machine that
    #    has some VGs and LVs, then if you want to disambiguate them you run
    #    'vgchange -u' to get a new VG UUID.  However, there is no equivalent
    #    command to reset LV uuid, because LVM finds two LVs with the same UUID
    #    in VGs with different UUIDs to be unique enough.
    class Meta:
        identifier = GlobalId('uuid', 'vg')
        icon = 'lvm_lv'
        label = 'Logical volume'

    vg = attributes.ResourceReference()
    uuid = attributes.Uuid()
    name = attributes.String()

    def get_label(self):
        return "%s-%s" % (self.vg.name, self.name)

    """ This has to be a class method today because at the point we call it we only has the type not the object"""

    @classmethod
    def device_type(cls):
        return "lvm_volume"