#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin

# This plugin is special, it uses chroma-manager internals
# in a way that third party plugins can't/shouldn't/mustn't
from chroma_core.lib.storage_plugin.base_resource import HostsideResource
from chroma_core.models import ManagedHost
from settings import SERIAL_PREFERENCE
import re

version = 1


class PluginAgentResources(resources.Resource, HostsideResource):
    class Meta:
        identifier = GlobalId('host_id', 'plugin_name')

    host_id = attributes.Integer()
    plugin_name = attributes.String()

    def get_label(self):
        host = ManagedHost._base_manager.get(pk=self.host_id)
        return "%s" % host


class ScsiDevice(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId('serial_80', 'serial_83')
        label = "SCSI device"

    serial_80 = attributes.String()
    serial_83 = attributes.String()

    def get_label(self):
        for attr in SERIAL_PREFERENCE:
            if getattr(self, attr):
                return getattr(self, attr)


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


class Partition(resources.LogicalDrive):
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


class LvmVolume(resources.LogicalDrive):
    # Q: Why is this identified by LV UUID and VG UUID rather than just
    #    LV UUID?  Isn't the LV UUID unique enough?
    # A: We're matching LVM2's behaviour.  If you e.g. image a machine that
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


class Linux(Plugin):
    internal = True

    def teardown(self):
        self.log.debug("Linux.teardown")

    def agent_session_continue(self, host_id, data):
        # The agent plugin sends us another full report when it thinks something has changed
        self.agent_session_start(host_id, data)

    def agent_session_start(self, host_id, data):
        devices = data

        lv_block_devices = set()
        for vg, lv_list in devices['lvs'].items():
            for lv_name, lv in lv_list.items():
                try:
                    lv_block_devices.add(lv['block_device'])
                except KeyError:
                    # An inactive LV has no block device
                    pass
        mpath_block_devices = set()
        for mp_name, mp in devices['mpath'].items():
            mpath_block_devices.add(mp['block_device'])

        special_block_devices = lv_block_devices | mpath_block_devices
        for uuid, md_info in devices['mds'].items():
            special_block_devices.add(md_info['block_device'])

        def preferred_serial(bdev):
            for attr in SERIAL_PREFERENCE:
                if bdev[attr]:
                    return bdev[attr]
            return None

        # Scrub dodgy QEMU SCSI IDs
        for bdev in devices['devs'].values():
            qemu_pattern = "QEMU HARDDISK"
            if bdev['serial_80'] and bdev['serial_80'].find(qemu_pattern) != -1:
                # Virtual environments can set an ID that trails QEMU HARDDISK, in which case
                # we should pick that up, or this might not be a real ID at all.
                # We have seen at least "SQEMU    QEMU HARDDISK" and "SQEMU    QEMU HARDDISK  0"
                # for devices without manually set IDs, so apply a general condition that the trailing
                # portion must be more than N characters for us to treat it like an ID
                trailing_id = bdev['serial_80'].split(qemu_pattern)[1].strip()
                if len(trailing_id) < 4:
                    bdev['serial_80'] = None
                else:
                    bdev['serial_80'] = trailing_id
            if bdev['serial_83'] and bdev['serial_83'].find(qemu_pattern) != -1:
                bdev['serial_83'] = None

        # Create ScsiDevices
        res_by_serial = {}
        for bdev in devices['devs'].values():
            serial = preferred_serial(bdev)
            if not bdev['major_minor'] in special_block_devices:
                if serial != None and not serial in res_by_serial:
                    # NB it's okay to have multiple block devices with the same
                    # serial (multipath): we just store the serial+size once
                    node, created = self.update_or_create(ScsiDevice,
                            serial_80 = bdev['serial_80'],
                            serial_83 = bdev['serial_83'],
                            size = bdev['size'])
                    res_by_serial[serial] = node

        # Map major:minor string to LinuxDeviceNode
        major_minor_to_node_resource = {}

        # Create DeviceNodes for ScsiDevices and UnsharedDevices
        for bdev in devices['devs'].values():
            # Partitions: we will do these in a second pass once their
            # parents are in bdev_to_resource
            if bdev['parent'] != None:
                continue

            # Don't create ScsiDevices for devicemapper, mdraid
            if bdev['major_minor'] in special_block_devices:
                continue

            serial = preferred_serial(bdev)
            if serial != None:
                # Serial is set, so look up the ScsiDevice
                lun_resource = res_by_serial[serial]
                node, created = self.update_or_create(LinuxDeviceNode,
                                    parents = [lun_resource],
                                    logical_drive = lun_resource,
                                    host_id = host_id,
                                    path = bdev['path'])
                major_minor_to_node_resource[bdev['major_minor']] = node
            else:
                # Serial is not set, so create an UnsharedDevice
                device, created = self.update_or_create(UnsharedDevice,
                        path = bdev['path'],
                        size = bdev['size'])
                node, created = self.update_or_create(LinuxDeviceNode,
                        parents = [device],
                        logical_drive = device,
                        host_id = host_id,
                        path = bdev['path'])
                major_minor_to_node_resource[bdev['major_minor']] = node

        # Okay, now we've got ScsiDeviceNodes, time to build the devicemapper ones
        # on top of them.  These can come in any order and be nested to any depth.
        # So we have to build a graph and then traverse it to populate our resources.
        for bdev in devices['devs'].values():
            if bdev['major_minor'] in lv_block_devices:
                node, created = self.update_or_create(LinuxDeviceNode,
                                    host_id = host_id,
                                    path = bdev['path'])
            elif bdev['major_minor'] in mpath_block_devices:
                node, created = self.update_or_create(LinuxDeviceNode,
                                    host_id = host_id,
                                    path = bdev['path'])
            elif bdev['parent']:
                node, created = self.update_or_create(LinuxDeviceNode,
                        host_id = host_id,
                        path = bdev['path'])
            else:
                continue

            major_minor_to_node_resource[bdev['major_minor']] = node

        # Now all the LUNs and device nodes are in, create the links between
        # the DM block devices and their parent entities.
        vg_uuid_to_resource = {}
        for vg in devices['vgs'].values():
            # Create VG resource
            vg_resource, created = self.update_or_create(LvmGroup,
                    uuid = vg['uuid'],
                    name = vg['name'],
                    size = vg['size'])
            vg_uuid_to_resource[vg['uuid']] = vg_resource

            # Add PV block devices as parents of VG
            for pv_bdev in vg['pvs_major_minor']:
                if pv_bdev in major_minor_to_node_resource:
                    vg_resource.add_parent(major_minor_to_node_resource[pv_bdev])

        for vg, lv_list in devices['lvs'].items():
            for lv_name, lv in lv_list.items():
                vg_info = devices['vgs'][vg]
                vg_resource = vg_uuid_to_resource[vg_info['uuid']]

                # Make the LV a parent of its device node on this host
                lv_resource, created = self.update_or_create(LvmVolume,
                        parents = [vg_resource],
                        uuid = lv['uuid'],
                        name = lv['name'],
                        vg = vg_resource,
                        size = lv['size'])

                try:
                    lv_node = major_minor_to_node_resource[lv['block_device']]
                    lv_node.logical_drive = lv_resource
                    lv_node.add_parent(lv_resource)
                except KeyError:
                    # Inactive LVs have no block device
                    pass

        for mpath_alias, mpath in devices['mpath'].items():
            # Devices contributing to the multipath
            mpath_parents = [major_minor_to_node_resource[n['major_minor']] for n in mpath['nodes']]
            # The multipath device node
            mpath_node = major_minor_to_node_resource[mpath['block_device']]
            for p in mpath_parents:
                # All the mpath_parents should have the same logical_drive
                mpath_node.logical_drive = mpath_parents[0].logical_drive
                mpath_node.add_parent(p)

        for uuid, md_info in devices['mds'].items():
            md_res, created = self.update_or_create(MdRaid,
                    size = devices['devs'][md_info['block_device']]['size'],
                    uuid = uuid)
            node_res, created = self.update_or_create(LinuxDeviceNode,
                    parents = [md_res],
                    logical_drive = md_res,
                    host_id = host_id,
                    path = md_info['path'])
            for drive_bd in md_info['drives']:
                drive_res = major_minor_to_node_resource[drive_bd]
                md_res.add_parent(drive_res)
            major_minor_to_node_resource[md_info['block_device']] = node_res

        for bdev, (mntpnt, fstype) in devices['local_fs'].items():
            bdev_resource = major_minor_to_node_resource[bdev]
            self.update_or_create(LocalMount,
                    parents=[bdev_resource],
                    mount_point = mntpnt,
                    fstype = fstype)

        # Create Partitions (devices that have 'parent' set)
        for bdev in [x for x in devices['devs'].values() if x['parent']]:
            this_node = major_minor_to_node_resource[bdev['major_minor']]
            parent_resource = major_minor_to_node_resource[bdev['parent']]
            number = int(re.search("(\d+)$", bdev['path']).group(1))

            if not parent_resource.logical_drive:
                raise RuntimeError("Parent %s of %s has no logical drive" % (parent_resource, bdev))

            partition, created = self.update_or_create(Partition,
                    parents = [parent_resource],
                    container = parent_resource.logical_drive,
                    number = number,
                    size = bdev['size'])

            this_node.add_parent(partition)

    def update_scan(self, scannable_resource):
        pass
