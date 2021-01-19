# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
import json
from logging import DEBUG

from toolz import merge

from django.db import transaction

from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.models import HaCluster
from chroma_core.plugins.block_devices import get_devices
from chroma_core.services import log_register

from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

# This plugin is special, it uses chroma-manager internals
# in a way that third party plugins can't/shouldn't/mustn't
from chroma_core.lib.storage_plugin.base_resource import HostsideResource
from chroma_core.models import ManagedHost
from chroma_core.models import VolumeNode
from settings import SERIAL_PREFERENCE

log = log_register("plugin_runner")
log.setLevel(DEBUG)

version = 1


class PluginAgentResources(resources.Resource, HostsideResource):
    class Meta:
        identifier = GlobalId("host_id", "plugin_name")

    host_id = attributes.Integer()
    plugin_name = attributes.String()

    def get_label(self):
        host = ManagedHost._base_manager.get(pk=self.host_id)
        return "%s" % host


class ScsiDevice(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId("serial")
        label = "SCSI device"

    serial = attributes.String()

    def get_label(self):
        return self.serial


class UnsharedDevice(resources.LogicalDrive):
    class Meta:
        identifier = ScopedId("path")

    # Annoying duplication of this from the node, but it really
    # is the closest thing we have to a real ID.
    path = attributes.PosixPath()

    def get_label(self):
        hide_prefixes = ["/dev/disk/by-path/", "/dev/disk/by-id/"]
        path = self.path
        for prefix in hide_prefixes:
            if path.startswith(prefix):
                path = path[len(prefix) :]
                break

        return path


class LinuxDeviceNode(resources.DeviceNode):
    class Meta:
        identifier = ScopedId("path")


class Partition(resources.LogicalDriveSlice):
    class Meta:
        identifier = GlobalId("container", "number")

    number = attributes.Integer()
    container = attributes.ResourceReference()

    def get_label(self):
        return "%s-%s" % (self.container.get_label(), self.number)


class MdRaid(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId("uuid")

    uuid = attributes.String()


class EMCPower(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId("uuid")

    uuid = attributes.String()


class LocalMount(resources.LogicalDriveOccupier):
    """Used for marking devices which are already in use, so that
    we don't offer them for use as Lustre targets."""

    class Meta:
        identifier = ScopedId("mount_point")

    fstype = attributes.String()
    mount_point = attributes.String()


class LvmGroup(resources.StoragePool):
    class Meta:
        identifier = GlobalId("uuid")
        icon = "lvm_vg"
        label = "Volume group"

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
        identifier = GlobalId("uuid", "vg")
        icon = "lvm_lv"
        label = "Logical volume"

    vg = attributes.ResourceReference()
    uuid = attributes.Uuid()
    name = attributes.String()

    def get_label(self):
        return "%s-%s" % (self.vg.name, self.name)

    """ This has to be a class method today because at the point we call it we only has the type not the object"""

    @classmethod
    def device_type(cls):
        return "lvm_volume"


class Linux(Plugin):
    internal = True

    def __init__(self, resource_manager, scannable_id=None):
        super(Linux, self).__init__(resource_manager, scannable_id)

        self.major_minor_to_node_resource = {}
        self.current_devices = "{}"

    def teardown(self):
        log.debug("Linux.teardown")

    def agent_session_continue(self, host_id, data):
        # The agent plugin sends us another full report when it thinks something has changed
        self.agent_session_start(host_id, data, initial_scan=False)

    def agent_session_start(self, host_id, data, initial_scan=True):
        with transaction.atomic():
            initiate_device_poll = False
            reported_device_node_paths = []

            host = ManagedHost.objects.get(id=host_id)
            fqdn = host.fqdn
            devices = get_devices(fqdn, timeout=5.0)

            if not devices:
                # use info from IML 4.0
                if data:
                    log.debug("Accept devices from incoming data")
                    devices = data
                elif host.immutable_state and initial_scan:
                    # It is highly unlikely that there's no data at all
                    # So on initial run we must wait for it as long as possible
                    # As in monitoring mode devices only delete if we leave too early
                    devices = get_devices(fqdn, 30.0)
                else:
                    return None

            for expected_item in ["vgs", "lvs", "devs", "local_fs", "mds", "mpath"]:
                if expected_item not in devices.keys():
                    devices[expected_item] = {}

            dev_json = json.dumps(devices["devs"], sort_keys=True)

            if dev_json == self.current_devices:
                return None

            log.debug("Linux.devices changed on {}".format(fqdn))

            log.debug(
                "old devices {}".format(set(json.loads(self.current_devices).keys()) - set(devices["devs"].keys()))
            )

            log.debug(
                "new devices {}".format(set(devices["devs"].keys()) - set(json.loads(self.current_devices).keys()))
            )

            self.current_devices = dev_json

            lv_block_devices = set()
            for vg, lv_list in devices["lvs"].items():
                for lv_name, lv in lv_list.items():
                    try:
                        lv_block_devices.add(lv["block_device"])
                    except KeyError:
                        # An inactive LV has no block device
                        pass

            mpath_block_devices = set()
            for mp_name, mp in devices["mpath"].items():
                mpath_block_devices.add(mp["block_device"])

            special_block_devices = lv_block_devices | mpath_block_devices

            for uuid, md_info in devices["mds"].items():
                special_block_devices.add(md_info["block_device"])

            def preferred_serial(bdev):
                for attr in SERIAL_PREFERENCE:
                    if bdev[attr]:
                        return bdev[attr]
                return None

            # Scrub dodgy QEMU SCSI IDs
            for bdev in devices["devs"].values():
                qemu_pattern = "QEMU HARDDISK"
                if bdev["serial_80"] and bdev["serial_80"].find(qemu_pattern) != -1:
                    # Virtual environments can set an ID that trails QEMU HARDDISK, in which case
                    # we should pick that up, or this might not be a real ID at all.
                    # We have seen at least "SQEMU    QEMU HARDDISK" and "SQEMU    QEMU HARDDISK  0"
                    # for devices without manually set IDs, so apply a general condition that the trailing
                    # portion must be more than N characters for us to treat it like an ID
                    trailing_id = bdev["serial_80"].split(qemu_pattern)[1].strip()
                    if len(trailing_id) < 4:
                        bdev["serial_80"] = None
                    else:
                        bdev["serial_80"] = trailing_id
                if bdev["serial_83"] and bdev["serial_83"].find(qemu_pattern) != -1:
                    bdev["serial_83"] = None

            # Create ScsiDevices
            res_by_serial = {}
            scsi_device_identifiers = []

            for bdev in devices["devs"].values():
                serial = preferred_serial(bdev)
                if not bdev["major_minor"] in special_block_devices:
                    if serial is not None and serial not in res_by_serial:
                        # NB it's okay to have multiple block devices with the same
                        # serial (multipath): we just store the serial+size once
                        node, created = self.update_or_create(
                            ScsiDevice, serial=serial, size=bdev["size"], filesystem_type=bdev["filesystem_type"]
                        )
                        res_by_serial[serial] = node
                        scsi_device_identifiers.append(node.id_tuple())

            # Map major:minor string to LinuxDeviceNode
            self.major_minor_to_node_resource = {}

            # Create DeviceNodes for ScsiDevices and UnsharedDevices
            for bdev in devices["devs"].values():
                # Partitions: we will do these in a second pass once their
                # parents are in bdev_to_resource
                if bdev["parent"] is not None:
                    continue

                # Don't create ScsiDevices for devicemapper, mdraid
                if bdev["major_minor"] in special_block_devices:
                    continue

                serial = preferred_serial(bdev)
                if serial is not None:
                    # Serial is set, so look up the ScsiDevice
                    lun_resource = res_by_serial[serial]
                    node, created = self.update_or_create(
                        LinuxDeviceNode,
                        parents=[lun_resource],
                        logical_drive=lun_resource,
                        host_id=host_id,
                        path=bdev["path"],
                    )
                    self.major_minor_to_node_resource[bdev["major_minor"]] = node
                    reported_device_node_paths.append(bdev["path"])
                else:
                    # Serial is not set, so create an UnsharedDevice
                    device, created = self.update_or_create(
                        UnsharedDevice, path=bdev["path"], size=bdev["size"], filesystem_type=bdev["filesystem_type"]
                    )
                    node, created = self.update_or_create(
                        LinuxDeviceNode, parents=[device], logical_drive=device, host_id=host_id, path=bdev["path"]
                    )
                    self.major_minor_to_node_resource[bdev["major_minor"]] = node
                    reported_device_node_paths.append(bdev["path"])

            # Okay, now we've got ScsiDeviceNodes, time to build the devicemapper ones
            # on top of them.  These can come in any order and be nested to any depth.
            # So we have to build a graph and then traverse it to populate our resources.
            for bdev in devices["devs"].values():
                if bdev["major_minor"] in lv_block_devices:
                    node, created = self.update_or_create(LinuxDeviceNode, host_id=host_id, path=bdev["path"])
                elif bdev["major_minor"] in mpath_block_devices:
                    node, created = self.update_or_create(LinuxDeviceNode, host_id=host_id, path=bdev["path"])
                elif bdev["parent"]:
                    node, created = self.update_or_create(LinuxDeviceNode, host_id=host_id, path=bdev["path"])
                else:
                    continue

                self.major_minor_to_node_resource[bdev["major_minor"]] = node
                reported_device_node_paths.append(bdev["path"])

            # Finally remove any of the scsi devs that are no longer present.
            initiate_device_poll |= self.remove_missing_devices(host_id, ScsiDevice, scsi_device_identifiers)

            # Now all the LUNs and device nodes are in, create the links between
            # the DM block devices and their parent entities.
            vg_uuid_to_resource = {}
            for vg in devices["vgs"].values():
                # Create VG resource
                vg_resource, created = self.update_or_create(
                    LvmGroup, uuid=vg["uuid"], name=vg["name"], size=vg["size"]
                )
                vg_uuid_to_resource[vg["uuid"]] = vg_resource

                # Add PV block devices as parents of VG
                for pv_bdev in vg["pvs_major_minor"]:
                    if pv_bdev in self.major_minor_to_node_resource:
                        vg_resource.add_parent(self.major_minor_to_node_resource[pv_bdev])

            for vg, lv_list in devices["lvs"].items():
                for lv_name, lv in lv_list.items():
                    vg_info = devices["vgs"][vg]
                    vg_resource = vg_uuid_to_resource[vg_info["uuid"]]

                    # Make the LV a parent of its device node on this host
                    lv_resource, created = self.update_or_create(
                        LvmVolume,
                        parents=[vg_resource],
                        uuid=lv["uuid"],
                        name=lv["name"],
                        vg=vg_resource,
                        size=lv["size"],
                        filesystem_type=devices["devs"][lv["block_device"]]["filesystem_type"],
                    )

                    try:
                        lv_node = self.major_minor_to_node_resource[lv["block_device"]]
                        lv_node.logical_drive = lv_resource
                        lv_node.add_parent(lv_resource)
                    except KeyError:
                        # Inactive LVs have no block device
                        pass

            for _, mpath in devices["mpath"].items():
                # Devices contributing to the multipath
                mpath_parents = [self.major_minor_to_node_resource[n["major_minor"]] for n in mpath["nodes"]]
                # The multipath device node
                mpath_node = self.major_minor_to_node_resource[mpath["block_device"]]
                for p in mpath_parents:
                    # All the mpath_parents should have the same logical_drive
                    mpath_node.logical_drive = mpath_parents[0].logical_drive
                    mpath_node.add_parent(p)

            self._map_drives_to_device_to_node(devices, host_id, "mds", MdRaid, [], reported_device_node_paths)

            for bdev, (mntpnt, fstype) in devices["local_fs"].items():
                if fstype != "lustre":
                    bdev_resource = self.major_minor_to_node_resource[bdev]
                    self.update_or_create(LocalMount, parents=[bdev_resource], mount_point=mntpnt, fstype=fstype)

            # Create Partitions (devices that have 'parent' set)
            partition_identifiers = []

            for bdev in [x for x in devices["devs"].values() if x["parent"]]:
                this_node = self.major_minor_to_node_resource[bdev["major_minor"]]
                parent_resource = self.major_minor_to_node_resource[bdev["parent"]]

                if not parent_resource.logical_drive:
                    raise RuntimeError("Parent %s of %s has no logical drive" % (parent_resource, bdev))

                partition, created = self.update_or_create(
                    Partition,
                    parents=[parent_resource],
                    container=parent_resource.logical_drive,
                    number=bdev["partition_number"],
                    size=bdev["size"],
                    filesystem_type=bdev["filesystem_type"],
                )

                this_node.add_parent(partition)
                partition_identifiers.append(partition.id_tuple())

            # Finally remove any of the partitions that are no longer present.
            initiate_device_poll |= self.remove_missing_devices(host_id, Partition, partition_identifiers)

            initiate_device_poll |= self.remove_missing_devicenodes(reported_device_node_paths)

        # If we see a device change and the data was sent by the agent poll rather than initial start up
        # then we need to cause all of the ha peer agents and any other nodes that we share VolumeNodes with
        # re-poll themselves.
        # This 'set' is probably a good balance between every node and no poll at all.
        if (initial_scan is False) and (initiate_device_poll is True):
            ha_peers = set(HaCluster.host_peers(ManagedHost.objects.get(id=host_id)))

            hosts_volume_node_ids = [
                volume_node.volume_id for volume_node in VolumeNode.objects.filter(host_id=host_id)
            ]
            all_volume_nodes = list(VolumeNode.objects.filter(volume_id__in=hosts_volume_node_ids))
            all_volume_node_hosts = ManagedHost.objects.filter(
                id__in=set(volume_node.host_id for volume_node in all_volume_nodes)
            )

            ha_peers |= set(all_volume_node_hosts)
            JobSchedulerClient.trigger_plugin_update([peer.id for peer in ha_peers], [host_id], ["linux"])

    def _map_drives_to_device_to_node(
        self, devices, host_id, device_type, klass, attributes_list, reported_device_node_paths
    ):
        resources_changed = False
        device_identifiers = []

        for device_uuid, device_info in devices[device_type].items():
            block_device = devices["devs"][device_info["block_device"]]

            node_attributes = {
                "size": block_device["size"],
                "filesystem_type": block_device["filesystem_type"],
                "uuid": device_uuid,
            }

            for attribute in attributes_list:
                node_attributes[attribute] = device_info[attribute]

            device_res, created_res = self.update_or_create(klass, **node_attributes)

            node_res, _ = self.update_or_create(
                LinuxDeviceNode,
                parents=[device_res],
                logical_drive=device_res,
                host_id=host_id,
                path=device_info["path"],
            )

            reported_device_node_paths.append(device_info["path"])
            device_identifiers.append(device_res.id_tuple())

            for drive_bd in device_info["drives"]:
                drive_res = self.major_minor_to_node_resource[drive_bd]
                device_res.add_parent(drive_res)

            self.major_minor_to_node_resource[device_info["block_device"]] = node_res

            resources_changed = created_res or resources_changed

        resources_changed |= self.remove_missing_devices(host_id, klass, device_identifiers)

        return resources_changed

    def remove_missing_devices(self, host_id, klass, device_identifiers):
        # Now look for any VolumeNodes that were not reported, these should be removed from the resources.
        # If there are no device_nodes left after this then remove the drive_resource as well.

        resources_changed = False

        for device_resource in self.find_by_attr(klass):
            if device_resource.id_tuple() not in device_identifiers:
                device_node_exists = False

                for resource_node in self.find_by_attr(LinuxDeviceNode):
                    if resource_node.logical_drive == device_resource:
                        if resource_node.host_id == host_id:
                            self.remove(resource_node)
                            resources_changed |= True
                        else:
                            device_node_exists = True

                if device_node_exists is False:
                    self.remove(device_resource)
                    resources_changed |= True

        return resources_changed

    def remove_missing_devicenodes(self, reported_paths):
        """
        Remove any LinuxDeviceNode paths that were not reported at all this iteration

        :param reported_paths: list of LinuxDeviceNode path's report on this iteration

        :return True if any resources were removed.
        """

        resources_changed = False

        for resource_node in self.find_by_attr(LinuxDeviceNode):
            if resource_node.path not in reported_paths:
                self.remove(resource_node)
                resources_changed |= True

        return resources_changed

    def update_scan(self, scannable_resource):
        pass
