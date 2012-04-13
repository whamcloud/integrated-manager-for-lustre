#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api.resources import Resource
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api.resources import   DeviceNode, LogicalDrive, StoragePool

# This plugin is special, it uses chroma-manager internals
# in a way that third party plugins can't/shouldn't/mustn't
from chroma_core.models import ManagedHost
from chroma_core.lib.storage_plugin.base_resource import HostsideResource

import re


class PluginAgentResources(Resource, HostsideResource):
    identifier = GlobalId('host_id', 'plugin_name')
    host_id = attributes.Integer()
    plugin_name = attributes.String()

    def get_label(self, parent = None):
        host = ManagedHost._base_manager.get(pk=self.host_id)
        return "%s" % host


class ScsiDevice(LogicalDrive):
    identifier = GlobalId('serial_80', 'serial_83')

    serial_80 = attributes.String()
    serial_83 = attributes.String()

    class_label = "SCSI device"

    def get_label(self, ancestors = []):
        if self.serial_80:
            QEMU_PREFIX = "SQEMU    QEMU HARDDISK  "
            if self.serial_80.find(QEMU_PREFIX) == 0:
                return self.serial_80[len(QEMU_PREFIX):]
            elif self.serial_80[0] == 'S':
                return self.serial_80[1:]
            else:
                return self.serial_80
        elif self.serial_83:
            return self.serial_83


class UnsharedDevice(LogicalDrive):
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


class LinuxDeviceNode(DeviceNode):
    identifier = ScopedId('path')


class Partition(LogicalDrive):
    identifier = GlobalId('container', 'number')
    number = attributes.Integer()
    container = attributes.ResourceReference()

    def get_label(self):
        return "%s-%s" % (self.container.get_label(), self.number)


class MdRaid(LogicalDrive):
    identifier = GlobalId('uuid')
    uuid = attributes.String()


class LocalMount(Resource):
    """Used for marking devices which are already in use, so that
    we don't offer them for use as Lustre targets."""
    identifier = ScopedId('mount_point')

    fstype = attributes.String()
    mount_point = attributes.String()


class LvmGroup(StoragePool):
    identifier = GlobalId('uuid')

    uuid = attributes.Uuid()
    name = attributes.String()
    size = attributes.Bytes()

    icon = 'lvm_vg'
    class_label = 'Volume group'

    def get_label(self, parent = None):
        return self.name


class LvmVolume(LogicalDrive):
    # Q: Why is this identified by LV UUID and VG UUID rather than just
    #    LV UUID?  Isn't the LV UUID unique enough?
    # A: We're matching LVM2's behaviour.  If you e.g. image a machine that
    #    has some VGs and LVs, then if you want to disambiguate them you run
    #    'vgchange -u' to get a new VG UUID.  However, there is no equivalent
    #    command to reset LV uuid, because LVM finds two LVs with the same UUID
    #    in VGs with different UUIDs to be unique enough.
    identifier = GlobalId('uuid', 'vg')

    vg = attributes.ResourceReference()
    uuid = attributes.Uuid()
    name = attributes.String()

    icon = 'lvm_lv'
    class_label = 'Logical volume'

    def get_label(self, ancestors = []):
        return "%s-%s" % (self.vg.name, self.name)


class Linux(Plugin):
    internal = True

    def __init__(self, *args, **kwargs):
        super(Linux, self).__init__(*args, **kwargs)

    def teardown(self):
        self.log.debug("Linux.teardown")

    def agent_session_continue(self, host_id, data):
        pass

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
            if bdev['serial_80']:
                return bdev['serial_80']
            elif bdev['serial_83']:
                return bdev['serial_83']
            else:
                return None

        # Create ScsiDevices
        res_by_serial = {}
        for bdev in devices['devs'].values():
            serial = preferred_serial(bdev)
            if not bdev['major_minor'] in special_block_devices:
                if serial != None and not serial in res_by_serial:
                    # NB it's okay to have multiple block devices with the same
                    # serial (multipath): we just store the serial+size once
                    res, created = self.update_or_create(ScsiDevice,
                            serial_80 = bdev['serial_80'],
                            serial_83 = bdev['serial_83'],
                            size = bdev['size'])
                    res_by_serial[serial] = res

        # Create DeviceNodes for ScsiDevices and UnsharedDevices
        bdev_to_resource = {}
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
                lun_resource = res_by_serial[serial]
                res, created = self.update_or_create(LinuxDeviceNode,
                                    parents = [lun_resource],
                                    logical_drive = lun_resource,
                                    host_id = host_id,
                                    path = bdev['path'])
            else:
                res, created = self.update_or_create(UnsharedDevice,
                        path = bdev['path'],
                        size = bdev['size'])
                res, created = self.update_or_create(LinuxDeviceNode,
                        parents = [res],
                        logical_drive = res,
                        host_id = host_id,
                        path = bdev['path'])
            bdev_to_resource[bdev['major_minor']] = res

        # Okay, now we've got ScsiDeviceNodes, time to build the devicemapper ones
        # on top of them.  These can come in any order and be nested to any depth.
        # So we have to build a graph and then traverse it to populate our resources.
        for bdev in devices['devs'].values():
            if bdev['major_minor'] in lv_block_devices:
                res, created = self.update_or_create(LinuxDeviceNode,
                                    host_id = host_id,
                                    path = bdev['path'])
            elif bdev['major_minor'] in mpath_block_devices:
                res, created = self.update_or_create(LinuxDeviceNode,
                                    host_id = host_id,
                                    path = bdev['path'])
            elif bdev['parent']:
                res, created = self.update_or_create(LinuxDeviceNode,
                        host_id = host_id,
                        path = bdev['path'])
            else:
                continue

            bdev_to_resource[bdev['major_minor']] = res

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
                if pv_bdev in bdev_to_resource:
                    vg_resource.add_parent(bdev_to_resource[pv_bdev])

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
                    lv_bdev = bdev_to_resource[lv['block_device']]
                    lv_bdev.add_parent(lv_resource)
                except KeyError:
                    # Inactive LVs have no block device
                    pass

        for mpath_alias, mpath in devices['mpath'].items():
            mpath_bdev = bdev_to_resource[mpath['block_device']]
            mpath_parents = [bdev_to_resource[n['major_minor']] for n in mpath['nodes']]
            for p in mpath_parents:
                mpath_bdev.add_parent(p)

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
                drive_res = bdev_to_resource[drive_bd]
                md_res.add_parent(drive_res)
            bdev_to_resource[md_info['block_device']] = node_res

        for bdev, (mntpnt, fstype) in devices['local_fs'].items():
            bdev_resource = bdev_to_resource[bdev]
            self.update_or_create(LocalMount,
                    parents=[bdev_resource],
                    mount_point = mntpnt,
                    fstype = fstype)

        for bdev in devices['devs'].values():
            if bdev['parent'] == None:
                continue

            this_node = bdev_to_resource[bdev['major_minor']]
            parent_resource = bdev_to_resource[bdev['parent']]
            number = int(re.search("(\d+)$", bdev['path']).group(1))

            assert(parent_resource.logical_drive)
            partition, created = self.update_or_create(Partition,
                    parents = [parent_resource],
                    container = parent_resource.logical_drive,
                    number = number,
                    size = bdev['size'])

            this_node.add_parent(partition)

    def update_scan(self, scannable_resource):
        pass
