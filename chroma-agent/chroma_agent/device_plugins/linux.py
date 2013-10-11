#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


from chroma_agent.log import console_log
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent import shell
from chroma_agent.utils import normalize_device, BlkId

import os
import glob
import re


class LinuxDevicePlugin(DevicePlugin):
    def _quick_scan(self):
        """Lightweight enumeration of available block devices"""
        return os.listdir("/sys/block/")

    def _full_scan(self):
        # Map of block devices major:minors to /dev/ path.
        block_devices = BlockDevices()

        # Devicemapper: LVM and Multipath
        dmsetup = DmsetupTable(block_devices)

        # Software RAID
        mds = MdRaid(block_devices).all()

        # Local filesystems (not lustre) in /etc/fstab or /proc/mounts
        local_fs = LocalFilesystems(block_devices).all()

        return {"vgs": dmsetup.vgs,
                "lvs": dmsetup.lvs,
                "mpath": dmsetup.mpaths,
                "devs": block_devices.block_device_nodes,
                "local_fs": local_fs,
                'mds': mds}

    def start_session(self):
        self._devices = self._quick_scan()
        return self._full_scan()

    def update_session(self):
        devices = self._quick_scan()
        if devices != self._devices:
            self._devices = devices
            return self._full_scan()


class DeviceHelper(object):
    """Base class with common methods for the various device detecting classes used
       by this plugin"""

    def _dev_major_minor(self, path):
        """Return a string if 'path' is a block device or link to one, else return None"""
        from stat import S_ISBLK
        try:
            s = os.stat(path)
        except OSError:
            return None

        if S_ISBLK(s.st_mode):
            return "%d:%d" % (os.major(s.st_rdev), os.minor(s.st_rdev))
        else:
            return None


class BlockDevices(DeviceHelper):
    """Reads /sys/block to detect all block devices, resolves SCSI WWIDs where possible, and
    generates a mapping of major:minor to normalized device node path and vice versa."""

    def __init__(self):
        self.old_udev = None

        # Build this map to retrieve fstype in _device_node
        self._major_minor_to_fstype = {}
        for blkid_dev in BlkId().all():
            major_minor = self._dev_major_minor(blkid_dev['path'])
            self._major_minor_to_fstype[major_minor] = blkid_dev['type']

        self.block_device_nodes, self.node_block_devices = self._parse_sys_block()

    def _device_node(self, device_name, major_minor, path, size, parent):
        # Old (RHEL5) version of scsi_id has a different command line
        # syntax to new (RHEL6) version.  Tell them apart with --version
        # (old one doesn't have --version, new one does)
        SCSI_ID_PATH = "/sbin/scsi_id"
        if self.old_udev is None:
            rc, out, err = shell.run([SCSI_ID_PATH, '--version'])
            self.old_udev = (rc != 0)

        def scsi_id_command(cmd):
            rc, out, err = shell.run(cmd)
            if rc:
                return None
            else:
                return out.strip()

        if self.old_udev:
            # Old scsi_id, operates on a /sys reference
            serial_80 = scsi_id_command(["scsi_id", "-g", "-p", "0x80", "-s", "/block/%s" % device_name])
            serial_83 = scsi_id_command(["scsi_id", "-g", "-p", "0x83", "-s", "/block/%s" % device_name])
        else:
            # New scsi_id, always operates directly on a device
            serial_80 = scsi_id_command(["scsi_id", "-g", "-p", "0x80", path])
            serial_83 = scsi_id_command(["scsi_id", "-g", "-p", "0x83", path])

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
        def _find_block_devs(folder):
            # Map of major_minor to path
            result = {}
            for path in glob.glob(os.path.join(folder, "*")):
                mm = self._dev_major_minor(path)
                if mm:
                    result[mm] = path

            return result

        mapper_devs = _find_block_devs("/dev/mapper/")
        by_id_nodes = _find_block_devs("/dev/disk/by-id/")
        by_path_nodes = _find_block_devs("/dev/disk/by-path/")

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
                import errno
                # Python errno doesn't include this code
                NO_MEDIA_ERRNO = 123
                if e.errno == errno.EROFS or e.errno == NO_MEDIA_ERRNO:
                    return

            # Resolve a major:minor to a /dev/foo
            path = normalize_device(get_path(major_minor, device_name))
            if path:
                block_device_nodes[major_minor] = self._device_node(device_name, major_minor, path, size, parent)
                node_block_devices[path] = major_minor

            return major_minor

        for dev_dir in glob.glob("/sys/block/*"):
            major_minor = parse_block_dir(dev_dir)

            partitions = glob.glob(os.path.join(dev_dir, "*/dev"))
            for p in partitions:
                parse_block_dir(os.path.split(p)[0], parent = major_minor)

        return block_device_nodes, node_block_devices


class LocalFilesystems(DeviceHelper):
    """Reads /proc/mounts and /etc/fstab to generate a map of block devices
    occupied by local filesystems"""

    def __init__(self, block_devices):
        from chroma_agent.utils import Fstab, Mounts
        fstab = Fstab()
        mounts = Mounts()
        from itertools import chain
        bdev_to_local_fs = {}
        for dev, mntpnt, fstype in chain(fstab.all(), mounts.all()):
            major_minor = self._dev_major_minor(dev)
            if major_minor and fstype != 'lustre' and major_minor in block_devices.block_device_nodes:
                bdev_to_local_fs[major_minor] = (mntpnt, fstype)

        self.bdev_to_local_fs = bdev_to_local_fs

    def all(self):
        return self.bdev_to_local_fs


class MdRaid(DeviceHelper):
    """Reads /proc/mdstat"""

    def __init__(self, block_devices):
        self.block_devices = block_devices

        mds = {}
        for md in self._get_md():
            drives = [self._dev_major_minor(dp) for dp in md['device_paths']]

            # Check that none of the drives in the array are None (i.e. not found) if we found them all
            # then we create the mds entry.
            if drives.count(None) == 0:
                mds[md['uuid']] = {'path': md["path"], 'block_device': md['mm'], 'drives': drives}

        self.mds = mds

    def all(self):
        return self.mds

    def _get_md(self):
        try:
            matches = re.finditer("^(md\d+) : active", open('/proc/mdstat').read().strip(), flags = re.MULTILINE)
            devs = []
            for match in matches:
                # e.g. md0
                device_name = match.group(1)
                device_path = "/dev/%s" % device_name
                device_major_minor = self._dev_major_minor(device_path)

                try:
                    detail = shell.try_run(['mdadm', '--brief', '--detail', '--verbose', device_path])
                    device_uuid = re.search("UUID=(.*)[ \\n]", detail.strip(), flags = re.MULTILINE).group(1)
                    device_list_csv = re.search("^\s+devices=(.*)$", detail.strip(), flags = re.MULTILINE).group(1)
                    device_list = device_list_csv.split(",")

                    devs.append({
                        "uuid": device_uuid,
                        "path": device_path,
                        "mm": device_major_minor,
                        "device_paths": device_list
                        })
                except OSError as os_error:
                    # mdadm doesn't exist, threw an error etc.
                    console_log.exception("mdadm threw an exception '%s' " % os_error.strerror)

            return devs
        except IOError:
            return []

class DmsetupTable(object):
    """Uses various devicemapper commands to learn about LVM and Multipath"""

    def __init__(self, block_devices):
        self.block_devices = block_devices
        self.mpaths = {}
        self.vgs = {}
        self.lvs = {}

        for vg_name, vg_uuid, vg_size in self._get_vgs():
            self.vgs[vg_name] = {
                'name': vg_name,
                'uuid': vg_uuid,
                'size': vg_size,
                'pvs_major_minor': []}
            self.lvs[vg_name] = {}
            for lv_name, lv_uuid, lv_size, lv_path in self._get_lvs(vg_name):
                self.lvs[vg_name][lv_name] = {
                    'name': lv_name,
                    'uuid': lv_uuid,
                    'size': lv_size}

        stdout = shell.try_run(['dmsetup', 'table'])
        self._parse_dm_table(stdout)

    def _get_vgs(self):
        out = shell.try_run(["vgs", "--units", "b", "--noheadings", "-o", "vg_name,vg_uuid,vg_size"])

        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            name, uuid, size_str = line.split()
            size = int(size_str[0:-1], 10)
            yield (name, uuid, size)

    def _get_lvs(self, vg_name):
        out = shell.try_run(["lvs", "--units", "b", "--noheadings", "-o", "lv_name,lv_uuid,lv_size,lv_path", vg_name])

        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            name, uuid, size_str, path = line.split()
            size = int(size_str[0:-1], 10)
            yield (name, uuid, size, path)

    def _parse_multipath_params(self, tokens):
        """
        Parse a multipath line from 'dmsetup table', starting after 'multipath'
        """
        # We will modify this, take a copy
        tokens = list(tokens)

        # integer count arguments, followed by list of strings
        n_feature_args = int(tokens[0])
        #feature_args = tokens[1:1 + n_feature_args]
        tokens = tokens[n_feature_args + 1:]

        # integer count arguments, followed by list of strings
        n_handler_args = int(tokens[0])
        #handler_args = tokens[1:1 + n_handler_args]
        tokens = tokens[n_handler_args + 1:]

        #num_groups, init_group_number = int(tokens[0]), int(tokens[1])
        tokens = tokens[2:]

        devices = []

        while len(tokens):
            path_selector, status, path_count, path_arg_count = tokens[0:4]

            # Sanity check of parsing, is the path selector one of those in 2.6.x linux kernel
            assert path_selector in ['round-robin', 'queue-length', 'service-time']
            path_arg_count = int(path_arg_count)
            path_count = int(path_count)

            # status is a call to ps.type->status with path=NULL, which for all linux 2.6 path selectors is always "0"
            # path_count is the number of paths in this priority group
            # path_arg_count is the number of args that each path will have after the block device identifier (a constant
            # for each path_selector)

            tokens = tokens[4:]
            for i in range(0, path_count):
                major_minor = tokens[0]
                # path_status_args = tokens[1:1 + path_arg_count]
                # The meaning of path_status_args depends on path_selector:
                #  for round-robin, and queue-length it is repeat_count (1 integer)
                #  for service-time it is repeat_count then relative_throughput (2 integers)
                tokens = tokens[1 + path_arg_count:]
                devices.append(major_minor)

        return devices

    def _parse_dm_table(self, stdout):
        if stdout.strip() == "No devices found":
            dm_lines = []
        else:
            dm_lines = [i for i in stdout.split("\n") if len(i) > 0]

        # Compose a lookup of names of multipath devices, for use
        # in parsing other lines
        multipath_names = set()
        for line in dm_lines:
            tokens = line.split()
            name = tokens[0].strip(":")
            dm_type = tokens[3]
            if dm_type == 'multipath':
                multipath_names.add(name)

        def _read_lv(block_device, lv_name, vg_name, devices):
            self.lvs[vg_name][lv_name]['block_device'] = block_device

            devices = [self.block_devices.block_device_nodes[i]['major_minor'] for i in devices]
            self.vgs[vg_name]['pvs_major_minor'] = list(set(self.vgs[vg_name]['pvs_major_minor']) | set(devices))

        def _read_lv_partition(block_device, parent_lv_name, vg_name):
            # HYD-744: FIXME: compose path in a way that copes with hyphens
            parent_block_device = self.block_devices.node_block_devices["/dev/mapper/%s-%s" % (vg_name, parent_lv_name)]
            self.block_devices.block_device_nodes[block_device]['parent'] = parent_block_device

        def _read_mpath_partition(block_device, parent_mpath_name):
            # A non-LV partition
            parent_block_device = self.block_devices.node_block_devices["/dev/mapper/%s" % parent_mpath_name]
            self.block_devices.block_device_nodes[block_device]['parent'] = parent_block_device

        # Make a note of which VGs/LVs are in the table so that we can
        # filter out nonlocal LVM components.
        local_lvs = set()
        local_vgs = set()

        for line in dm_lines:
            tokens = line.split()
            name = tokens[0].strip(":")
            dm_type = tokens[3]

            node_path = os.path.join("/dev/mapper", name)
            block_device = self.block_devices.node_block_devices[node_path]

            if dm_type in ['linear', 'striped']:
                # This is either an LV or a partition.
                # Try to resolve its name to a known LV, if not found then it
                # is a partition.
                # This is an LVM LV
                if dm_type == 'striped':
                    # List of striped devices
                    dev_indices = range(6, len(tokens), 2)
                    devices = [tokens[i] for i in dev_indices]
                elif dm_type == 'linear':
                    # Single device linear range
                    devices = [tokens[4]]
                else:
                    console_log.error("Failed to parse dmsetupline '%s'" % line)
                    continue

                # To be an LV:
                #  Got to have a hyphen
                #  Got to appear in lvs dict

                # To be a partition:
                #  Got to have a (.*)p\d+$
                #  Part preceeding that pattern must be an LV or a mpath

                # Potentially confusing scenarios:
                #  A multipath device named foo-bar where there exists a VG called 'foo'
                #  An LV whose name ends "p1" like foo-lvp1
                #  NB some scenarios may be as confusing for devicemapper as they are for us, e.g.
                #  if someone creates an LV "bar" in a VG "foo", and also an mpath called "foo-bar"

                # First, let's see if it's an LV or an LV partition
                match = re.search("(.*[^-])-([^-].*)", name)
                if match:
                    vg_name, lv_name = match.groups()
                    # When a name has a "-" in it, DM prints a double hyphen in the output
                    # So for an LV called "my-lv" you get VolGroup00-my--lv
                    vg_name = vg_name.replace("--", "-")
                    lv_name = lv_name.replace("--", "-")
                    try:
                        vg_lv_info = self.lvs[vg_name]
                        local_vgs.add(vg_name)
                    except KeyError:
                        # Part before the hyphen is not a VG, so this can't be an LV
                        pass
                    else:
                        if lv_name in vg_lv_info:
                            _read_lv(block_device, lv_name, vg_name, devices)
                            local_lvs.add(lv_name)
                            continue
                        else:
                            # It's not an LV, but it matched a VG, could it be an LV partition?
                            result = re.search("(.*)p\d+", lv_name)
                            if result:
                                lv_name = result.groups()[0]
                                if lv_name in vg_lv_info:
                                    # This could be an LV partition.
                                    _read_lv_partition(block_device, lv_name, vg_name)
                                    local_lvs.add(lv_name)
                                    continue
                else:
                    # If it isn't an LV or an LV partition, see if it looks like an mpath partition
                    result = re.search("(.*)p\d+", name)
                    if result:
                        mpath_name = result.groups()[0]
                        if mpath_name in multipath_names:
                            _read_mpath_partition(block_device, mpath_name)
                        else:
                            # Part before p\d+ is not an mpath, therefore not a multipath partition
                            pass
                    else:
                        # No trailing p\d+, therefore not a partition
                        console_log.error("Cannot handle devicemapper device %s: it doesn't look like an LV or a partition" % name)
            elif dm_type == 'multipath':
                major_minors = self._parse_multipath_params(tokens[4:])
                devices = [self.block_devices.block_device_nodes[i] for i in major_minors]
                if name in self.mpaths:
                    raise RuntimeError("Duplicated mpath device %s" % name)

                self.mpaths[name] = {
                    "name": name,
                    "block_device": block_device,
                    "nodes": devices
                }
            else:
                continue

        # Filter out nonlocal LVM components (HYD-2431)
        for vg_name, vg_lvs in self.lvs.items():
            if vg_name not in local_vgs:
                del self.lvs[vg_name]
                del self.vgs[vg_name]
                continue

            for lv_name in vg_lvs:
                if lv_name not in local_lvs:
                    del self.lvs[vg_name][lv_name]
