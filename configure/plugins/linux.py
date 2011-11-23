
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.lib.storage_plugin.plugin import StoragePlugin
from configure.lib.storage_plugin.resource import StorageResource, ScannableId, GlobalId, ScannableResource

from configure.lib.storage_plugin import attributes
from configure.lib.storage_plugin import base_resources
from configure.lib.storage_plugin import alert_conditions
from configure.lib.storage_plugin import statistics

# This plugin is special, it uses Hydra's built-in infrastructure
# in a way that third party plugins can't/shouldn't/mustn't
from configure.lib.agent import Agent
from configure.models import ManagedHost


class DeviceNode(StorageResource):
    # NB ideally we would get this from exploring the graph rather than
    # tagging it onto each one, but this is simpler for now - jcs
    host = attributes.ResourceReference()
    path = attributes.PosixPath()
    human_name = 'Device node'

    def human_string(self):
        path = self.path
        strip_strings = ["/dev/",
                         "/dev/mapper/",
                         "/dev/disk/by-id/",
                         "/dev/disk/by-path/"]
        strip_strings.sort(lambda a, b: cmp(len(b), len(a)))
        for s in strip_strings:
            if path.startswith(s):
                path = path[len(s):]
        return "%s:%s" % (self.host.human_string(), path)


class HydraHostProxy(StorageResource, ScannableResource):
    # FIXME using address here is troublesome for hosts whose
    # addresses might change.  However it is useful for doing
    # an update_or_create on VMs discovered on controllers.  Hmm.
    # I wonder if what I really want is a HostResource base and then
    # subclasses for on-controller hosts (identified by controller+index)
    # and separately for general hosts (identified by ManagedHost.pk)
    identifier = GlobalId('host_id')

    host_id = attributes.Integer()
    virtual_machine = attributes.ResourceReference(optional = True)

    def human_string(self, parent = None):
        host = ManagedHost._base_manager.get(pk=self.host_id)
        return "%s" % host

# Things to offer the user when formatting
# all of the below must NOT be offered if they have an LVM VG descendent
# or a NonLustreFilesystem descendent
# * ScsiDevice (i.e. shared LUNs like DDN VDs) IF it has no LV descendents
# * UnsharedDeviceNode (i.e. IDE or virtio devices)
# * LvmVolume
#
# For any of the above, we must also work out their leaf device nodes, which
# should be just the leaf resources.

HACK_TEST_STATS = False


class ScsiDevice(base_resources.LogicalDrive):
    identifier = GlobalId('serial')

    serial = attributes.String(subscribe = 'scsi_serial')

    human_name = "SCSI device"

    if HACK_TEST_STATS:
        test_stat = statistics.Gauge()
        test_hist = statistics.BytesHistogram(bins = [(0, 256), (257, 512), (513, 2048), (2049, 8192)])
        beef_alert = alert_conditions.AttrValAlertCondition('serial', warn_states = ['SQEMU    QEMU HARDDISK  WD-deadbeef0'], message = "Beef alert in sector 2!")

    def human_string(self, ancestors = []):
        qemu_strip_hack = "SQEMU    QEMU HARDDISK  "

        if self.serial.startswith(qemu_strip_hack):
            # FIXME: this is a hack that I'm doing for demos because we're not getting SCSI serials in parts yet
            return self.serial[len(qemu_strip_hack):]
        elif self.serial[0] == 'S':
            return self.serial[1:]
        else:
            return self.serial


class UnsharedDeviceNode(DeviceNode):
    """A device node whose underlying device has no SCSI ID
    and is therefore assumed to be unshared"""
    identifier = ScannableId('path')

    human_name = "Local disk"

    def human_string(self, ancestors = []):
        if self.path.startswith("/dev/"):
            return self.path[5:]
        else:
            return self.path


class UnsharedDevice(base_resources.LogicalDrive):
    identifier = ScannableId('path')
    # Annoying duplication of this from the node, but it really
    # is the closest thing we have to a real ID.
    path = attributes.PosixPath()

    def human_string(self):
        return self.path


class ScsiDeviceNode(DeviceNode):
    """SCSI in this context is a catch-all to refer to
    block devices which look like real disks to the host OS"""
    identifier = ScannableId('path')
    #human_name = "SCSI device node"
    host = attributes.ResourceReference()


class MultipathDeviceNode(DeviceNode):
    identifier = ScannableId('path')
    human_name = "Multipath device node"


class LvmDeviceNode(DeviceNode):
    identifier = ScannableId('path')
    human_name = "LVM device node"

    def human_string(self):
        # LVM devices are only presented once per host,
        # so just need to say which host this device node is for
        return "%s" % (self.host.human_string())


# FIXME: partitions should really be GlobalIds (they can be seen from more than
# one host) where the ID is their number plus the a foreign key to the parent
# ScsiDevice or UnsharedDevice(HYD-272)
# TODO: include containng object human_string in partition human_string
class Partition(base_resources.LogicalDrive):
    identifier = ScannableId('path')
    human_name = "Linux partition"
    path = attributes.PosixPath()

    def human_string(self):
        return self.path


class PartitionDeviceNode(DeviceNode):
    identifier = ScannableId('path')
    human_name = "Linux partition"


class LocalMount(StorageResource):
    """A local filesystem consuming a storage resource -- reported so that
       hydra knows not to try and use the consumed resource for Lustre e.g.
       minor things like your root partition."""
    identifier = ScannableId('mount_point')

    fstype = attributes.String()
    mount_point = attributes.String()


class Linux(StoragePlugin):
    def __init__(self, *args, **kwargs):
        super(Linux, self).__init__(*args, **kwargs)

        self._scsi_devices = set()

    def teardown(self):
        self.log.debug("Linux.teardown")

    # TODO: need to document that initial_scan may not kick off async operations, because
    # the caller looks at overall resource state at exit of function.  If they eg
    # want to kick off an async update thread they should do it at the first
    # call to update_scan, or maybe we could give them a separate function for that.
    def initial_scan(self, root_resource):
        host = ManagedHost.objects.get(pk=root_resource.host_id)

        self.agent = Agent(host = host, log = self.log)
        devices = self.agent.invoke("device-scan")

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

        dm_block_devices = lv_block_devices | mpath_block_devices

        # List of BDs with serial numbers that aren't devicemapper BDs
        devs_by_serial = {}
        for bdev in devices['devs'].values():
            serial = bdev['serial']
            if not bdev['major_minor'] in dm_block_devices:
                if serial != None and not serial in devs_by_serial:
                    # NB it's okay to have multiple block devices with the same
                    # serial (multipath): we just store the serial+size once
                    devs_by_serial[serial] = {
                            'serial': serial,
                            'size': bdev['size']
                            }

        # Resources for devices with serial numbers
        res_by_serial = {}
        for dev in devs_by_serial.values():
            res, created = self.update_or_create(ScsiDevice, serial = dev['serial'], size = dev['size'])
            self._scsi_devices.add(res)
            res_by_serial[dev['serial']] = res

        bdev_to_resource = {}
        for bdev in devices['devs'].values():
            # Partitions: we will do these in a second pass once their
            # parents are in bdev_to_resource
            if bdev['parent'] != None:
                continue

            # DM devices: we will do these later
            if bdev['major_minor'] in dm_block_devices:
                continue

            if bdev['serial'] != None:
                lun_resource = res_by_serial[bdev['serial']]
                res, created = self.update_or_create(ScsiDeviceNode,
                                    parents = [lun_resource],
                                    host = root_resource,
                                    path = bdev['path'])
            else:
                res, created = self.update_or_create(UnsharedDevice,
                        path = bdev['path'],
                        size = bdev['size'])
                res, created = self.update_or_create(UnsharedDeviceNode,
                        parents = [res],
                        host = root_resource,
                        path = bdev['path'])
            bdev_to_resource[bdev['major_minor']] = res

        # Okay, now we've got ScsiDeviceNodes, time to build the devicemapper ones
        # on top of them.  These can come in any order and be nested to any depth.
        # So we have to build a graph and then traverse it to populate our resources.
        for bdev in devices['devs'].values():
            if bdev['major_minor'] in lv_block_devices:
                res, created = self.update_or_create(LvmDeviceNode,
                                    host = root_resource,
                                    path = bdev['path'])
            elif bdev['major_minor'] in mpath_block_devices:
                res, created = self.update_or_create(MultipathDeviceNode,
                                    host = root_resource,
                                    path = bdev['path'])
            elif bdev['parent']:
                res, created = self.update_or_create(PartitionDeviceNode,
                        host = root_resource,
                        path = bdev['path'])
            else:
                continue

            bdev_to_resource[bdev['major_minor']] = res

        for bdev in devices['devs'].values():
            if bdev['parent'] == None:
                continue

            this_node = bdev_to_resource[bdev['major_minor']]
            parent_resource = bdev_to_resource[bdev['parent']]

            partition, created = self.update_or_create(Partition,
                    parents = [parent_resource],
                    size = bdev['size'],
                    path = bdev['path'])

            this_node.add_parent(partition)

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

        for bdev, (mntpnt, fstype) in devices['local_fs'].items():
            bdev_resource = bdev_to_resource[bdev]
            self.update_or_create(LocalMount,
                    parents=[bdev_resource],
                    mount_point = mntpnt,
                    fstype = fstype)

    def update_scan(self, scannable_resource):
        if HACK_TEST_STATS:
            for scsi_dev in list(self._scsi_devices):
                import random
                num = random.randint(10, 20)
                scsi_dev.test_stat = num
                scsi_dev.test_hist = [random.randint(50, 100) for r in range(0, 4)]


class LvmGroup(base_resources.StoragePool):
    identifier = GlobalId('uuid')

    uuid = attributes.Uuid()
    name = attributes.String()
    size = attributes.Bytes()

    icon = 'lvm_vg'
    human_name = 'Volume group'

    def human_string(self, parent = None):
        return self.name


class LvmVolume(base_resources.LogicalDrive):
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
    human_name = 'Logical volume'

    def human_string(self, ancestors = []):
        return "%s-%s" % (self.vg.name, self.name)
