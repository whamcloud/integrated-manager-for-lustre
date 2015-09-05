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


import os
import glob
import re
import errno

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent import utils
from chroma_agent import config
import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.device_plugins.linux_components.device_helper import DeviceHelper
from chroma_agent.device_plugins.linux_components.zfs import ZfsDevices
from chroma_agent.device_plugins.linux_components.device_mapper import DmsetupTable
from chroma_agent.device_plugins.linux_components.emcpower import EMCPower
from chroma_agent.device_plugins.linux_components.local_filesystems import LocalFilesystems
from chroma_agent.device_plugins.linux_components.mdraid import MdRaid
# Python errno doesn't include this code
errno.NO_MEDIA_ERRNO = 123


class LinuxDevicePlugin(DevicePlugin):
    # Some places require that the devices have been scanned before then can operate correctly, this is because the
    # scan creates and stores some information that is use in other places. This is non-optimal because it gives the
    # agent some state which we try and avoid. But this flag does at least allow us to keep it neat.
    devices_scanned = False

    def _quick_scan(self):
        """Lightweight enumeration of available block devices"""
        zfs = ZfsDevices().quick_scan()
        blocks = os.listdir("/sys/block/")

        return zfs + blocks

    def _full_scan(self):
        # If we are a worker node then return nothing because our devices are not of interest. This is a short term
        # solution for HYD-3140. This plugin should really be loaded if it is not needed but for now this sorts out
        # and issue with PluginAgentResources being in the linux plugin.
        if config.get('settings', 'profile')['worker']:
            return {}

        # Map of block devices major:minors to /dev/ path.
        block_devices = BlockDevices()

        # Devicemapper: LVM and Multipath
        dmsetup = DmsetupTable(block_devices)

        # Software RAID
        mds = MdRaid(block_devices).all()

        # _zpools
        zfs_devices = ZfsDevices()
        zfs_devices.full_scan(block_devices)

        # EMCPower Devices
        emcpowers = EMCPower(block_devices).all()

        # Local filesystems (not lustre) in /etc/fstab or /proc/mounts
        local_fs = LocalFilesystems(block_devices).all()

        # We have scan devices, so set the devices scanned flags.
        LinuxDevicePlugin.devices_scanned = True

        return {"vgs": dmsetup.vgs,
                "lvs": dmsetup.lvs,
                "zfspools": zfs_devices.zpools,
                "zfsdatasets": zfs_devices.datasets,
                "zfsvols": zfs_devices.zvols,
                "mpath": dmsetup.mpaths,
                "devs": block_devices.block_device_nodes,
                "local_fs": local_fs,
                'emcpower': emcpowers,
                'mds': mds}

    def start_session(self):
        self._devices = self._quick_scan()
        return self._full_scan()

    def update_session(self):
        devices = self._quick_scan()
        if devices != self._devices:
            self._devices = devices
            return self._full_scan()


class BlockDevices(DeviceHelper):
    """Reads /sys/block to detect all block devices, resolves SCSI WWIDs where possible, and
    generates a mapping of major:minor to normalized device node path and vice versa."""

    def __init__(self):
        self.old_udev = None

        # Build this map to retrieve fstype in _device_node
        self._major_minor_to_fstype = {}
        for blkid_dev in utils.BlkId().itervalues():
            major_minor = self._dev_major_minor(blkid_dev['path'])
            self._major_minor_to_fstype[major_minor] = blkid_dev['type']

        self.block_device_nodes, self.node_block_devices = self._parse_sys_block()

    def _device_node(self, device_name, major_minor, path, size, parent):
        # RHEL6 version of scsi_id is located at a different location to the RHEL7 version
        # work this out at the start then go with it.
        scsi_id_cmd = None

        for scsi_id_command in ["/sbin/scsi_id", "/lib/udev/scsi_id", ""]:
            if os.path.isfile(scsi_id_command):
                scsi_id_cmd = scsi_id_command

        if scsi_id_cmd == None:
            raise RuntimeError("Unabled to find scsi_id")

        def scsi_id_command(cmd):
            rc, out, err = AgentShell.run(cmd)
            if rc:
                return None
            else:
                return out.strip()

        # New scsi_id, always operates directly on a device
        serial_80 = scsi_id_command([scsi_id_cmd, "-g", "-p", "0x80", path])
        serial_83 = scsi_id_command([scsi_id_cmd, "-g", "-p", "0x83", path])

        try:
            type = self._major_minor_to_fstype[major_minor]
        except KeyError:
            type = None

        info = {'major_minor': major_minor,
                'path': path,
                'serial_80': serial_80,
                'serial_83': serial_83,
                'size': size,
                'filesystem_type': type,
                'parent': parent}

        return info

    def _parse_sys_block(self):
        mapper_devs = self._find_block_devs(self.MAPPERPATH)
        by_id_nodes = self._find_block_devs(self.DISKBYIDPATH)
        by_path_nodes = self._find_block_devs(self.DISKBYPATHPATH)
        dev_nodes = self._find_block_devs(self.DEVPATH)

        def get_path(major_minor, device_name):
            # Try to find device nodes for these:
            fallback_dev_path = os.path.join("/dev/", device_name)
            # * First look in /dev/mapper
            if major_minor in mapper_devs:
                return mapper_devs[major_minor]
            # * Then try /dev/disk/by-id
            elif major_minor in by_id_nodes:
                return by_id_nodes[major_minor]
            # * Then try /dev/disk/by-path
            elif major_minor in by_path_nodes:
                return by_path_nodes[major_minor]
            # * Then fall back to just /dev
            elif os.path.exists(fallback_dev_path):
                return fallback_dev_path
            else:
                console_log.warning("Could not find device node for %s (%s)" % (major_minor, fallback_dev_path))
                return None

        block_device_nodes = {}
        node_block_devices = {}

        def parse_block_dir(dev_dir, parent = None):
            """Parse a dir like /sys/block/sda (must contain 'dev' and 'size')"""
            device_name = dev_dir.split(os.sep)[-1]
            major_minor = open(os.path.join(dev_dir, "dev")).read().strip()
            size = int(open(os.path.join(dev_dir, "size")).read().strip()) * 512

            # Exclude zero-sized devices
            if not size:
                return

            # Exclude ramdisks, floppy drives, obvious cdroms
            if re.search("^ram\d+$", device_name) or\
               re.search("^fd\d+$", device_name) or\
               re.search("^sr\d+$", device_name):
                return

            # Exclude read-only or removed devices
            try:
                open("/dev/%s" % device_name, 'w')
            except IOError, e:
                if e.errno == errno.EROFS or e.errno == errno.NO_MEDIA_ERRNO:
                    return

            # Resolve a major:minor to a /dev/foo
            path = get_path(major_minor, device_name)
            if path:
                block_device_nodes[major_minor] = self._device_node(device_name, major_minor, path, size, parent)
                node_block_devices[path] = major_minor

            return major_minor

        for dev_dir in glob.glob("/sys/block/*"):
            major_minor = parse_block_dir(dev_dir)

            partitions = glob.glob(os.path.join(dev_dir, "*/dev"))
            for p in partitions:
                parse_block_dir(os.path.split(p)[0], parent = major_minor)

        # Finally create the normalized maps for /dev to /dev/disk/by-path & /dev/disk/by-id
        # and then /dev/disk/by-path & /dev/disk/by-id to /dev/mapper
        ndp.add_normalized_list(dev_nodes, by_path_nodes)
        ndp.add_normalized_list(dev_nodes, by_id_nodes)
        ndp.add_normalized_list(by_path_nodes, mapper_devs)
        ndp.add_normalized_list(by_id_nodes, mapper_devs)

        return block_device_nodes, node_block_devices
