#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2017 Intel Corporation All Rights Reserved.
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
import stat
import time

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log, daemon_log
from chroma_agent import utils
import chroma_agent.lib.normalize_device_path as ndp
# Python errno doesn't include this code
errno.NO_MEDIA_ERRNO = 123


class BlockDevices(object):
    """
    Reads /sys/block to detect all block devices, resolves SCSI WWIDs where possible, and
    generates a mapping of major:minor to normalized device node path and vice versa.
    """
    MAPPERPATH = os.path.join('/dev', 'mapper')
    DISKBYIDPATH = os.path.join('/dev', 'disk', 'by-id')
    DISKBYPATHPATH = os.path.join('/dev', 'disk', 'by-path')
    SYSBLOCKPATH = os.path.join('/sys', 'block')
    MDRAIDPATH = os.path.join('/dev', 'md')
    DEVPATH = '/dev'
    MAXRETRIES = 5
    non_existent_paths = set([])
    previous_path_status = {}

    def __init__(self):
        self.old_udev = None
        self._major_minor_to_fstype = {}  # Build this map to retrieve fstype in _device_node

        for blkid_dev in utils.BlkId().itervalues():
            major_minor = self._dev_major_minor(blkid_dev['path'])

            if major_minor:
                self._major_minor_to_fstype[major_minor] = blkid_dev['type']

        self.block_device_nodes, self.node_block_devices = self._parse_sys_block()

    def _dev_major_minor(self, path):
        """ Return a string if 'path' is a block device or link to one, else return None """

        file_status = None
        retries = self.MAXRETRIES
        while retries > 0:
            try:
                file_status = os.stat(path)

                if path in self.non_existent_paths:
                    self.non_existent_paths.discard(path)
                    daemon_log.debug('New device started to respond %s' % path)

                self.previous_path_status[path] = file_status
                break
            except OSError as os_error:
                if os_error.errno not in [errno.ENOENT, errno.ENOTDIR]:
                    raise

                # An OSError could be raised because a path genuinely doesn't
                # exist, but it also can be the result of conflicting with
                # actions that cause devices to disappear momentarily, such as
                # during a partprobe while it reloads the partition table.
                # So we retry for a short window to catch those devices that
                # just disappear momentarily.
                time.sleep(0.1)
                retries -= retries if path in self.non_existent_paths else 1

        if file_status is None:
            if path not in self.non_existent_paths:
                self.non_existent_paths.add(path)
                daemon_log.debug('New device failed to respond %s' % path)

            if path not in self.previous_path_status:
                return None

            file_status = self.previous_path_status.pop(path)
            daemon_log.debug('Device failed to respond but stored file_status used')

        if stat.S_ISBLK(file_status.st_mode):
            return "%d:%d" % (os.major(file_status.st_rdev), os.minor(file_status.st_rdev))
        else:
            return None

    def paths_to_major_minors(self, device_paths):
        """
        Create a list of device major minors for a list of device paths from _path_to_major_minor dict.
        If any of the paths come back as None, continue to the next.

        :param device_paths: The list of paths to get the list of major minors for.
        :return: list of dev_major_minors, or an empty list if any device_path is not found.
        """
        device_mms = []
        for device_path in device_paths:
            device_mm = self.path_to_major_minor(device_path)

            if device_mm is None:
                continue

            device_mms.append(device_mm)
        return device_mms

    def path_to_major_minor(self, device_path):
        """ Return device major minor for a given device path """
        return self.node_block_devices.get(ndp.normalized_device_path(device_path))

    def composite_device_list(self, source_devices):
        """
        This function takes a bunch of devices like MdRaid, EMCPower which are effectively composite devices made up
        from a collection of other devices and returns that list with the drives and everything nicely assembled.
        """
        devices = {}

        for device in source_devices:
            drive_mms = self.paths_to_major_minors(device['device_paths'])

            if drive_mms:
                devices[device['uuid']] = {'path': device["path"],
                                           'block_device': device['mm'],
                                           'drives': drive_mms}

                # Finally add these devices to the canonical path list.
                for device_path in device['device_paths']:
                    ndp.add_normalized_device(device_path, device['path'])

        return devices

    def find_block_devs(self, folder):
        # Map of major_minor to path
        result = {}
        for path in glob.glob(os.path.join(folder, "*")):
            mm = self._dev_major_minor(path)
            if mm:
                result[mm] = path

        return result

    def _device_node(self, major_minor, path, size, parent, partition_number):
        # RHEL6 version of scsi_id is located at a different location to the RHEL7 version
        # work this out at the start then go with it.
        scsi_id_cmd = None

        for scsi_id_command in ["/sbin/scsi_id", "/lib/udev/scsi_id", ""]:
            if os.path.isfile(scsi_id_command):
                scsi_id_cmd = scsi_id_command

        if scsi_id_cmd == None:
            raise RuntimeError("Unabled to find scsi_id")

        def scsi_id_command(cmd):
            rc, out, err = AgentShell.run_old(cmd)
            if rc:
                return None
            else:
                return out.strip()

        # New scsi_id, always operates directly on a device
        serial_80 = scsi_id_command([scsi_id_cmd, "-g", "-p", "0x80", path])
        serial_83 = scsi_id_command([scsi_id_cmd, "-g", "-p", "0x83", path])

        type = self._major_minor_to_fstype.get(major_minor)

        info = {'major_minor': major_minor,
                'path': path,
                'serial_80': serial_80,
                'serial_83': serial_83,
                'size': size,
                'filesystem_type': type,
                'partition_number': partition_number,
                'parent': parent}

        return info

    def _parse_sys_block(self):
        mapper_devs = self.find_block_devs(self.MAPPERPATH)
        by_id_nodes = self.find_block_devs(self.DISKBYIDPATH)
        by_path_nodes = self.find_block_devs(self.DISKBYPATHPATH)
        dev_nodes = self.find_block_devs(self.DEVPATH)

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
            """ Parse a dir like /sys/block/sda (must contain 'dev' and 'size') """
            size = 0
            device_name = dev_dir.split(os.sep)[-1]

            try:
                major_minor = open(os.path.join(dev_dir, "dev")).read().strip()
                size = int(open(os.path.join(dev_dir, "size")).read().strip()) * 512
            except IOError:
                pass

            # Exclude zero-sized devices
            if size == 0:
                return

            # Exclude ramdisks, floppy drives, obvious cdroms
            if re.search("^ram\d+$", device_name) or\
               re.search("^fd\d+$", device_name) or\
               re.search("^sr\d+$", device_name):
                return

            # Exclude read-only devices and removed media or devices
            try:
                # Never use 'w' in the built-in open() or it'll create a 0 length file where a
                # device was removed!
                fd = os.open("/dev/%s" % device_name, os.O_WRONLY)
            except OSError, e:
                # EROFS: Device is read-only
                # ENOENT: No such file or directory
                # NO_MEDIA_ERRNO: No medium found
                if e.errno in [errno.EROFS, errno.ENOENT, errno.NO_MEDIA_ERRNO]:
                    return
            else:
                os.close(fd)

            # Resolve a major:minor to a /dev/foo
            path = get_path(major_minor, device_name)
            if path:
                if parent:
                    partition_number = int(re.search("(\d+)$", device_name).group(1))
                else:
                    partition_number = None

                block_device_nodes[major_minor] = self._device_node(major_minor, path, size, parent, partition_number)
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

    @classmethod
    def quick_scan(cls):
        """ Return a very quick list of block devices from a number of sources so we can quickly see changes. """
        blocks = []

        for path in [cls.SYSBLOCKPATH, cls.MAPPERPATH, cls.DISKBYIDPATH, cls.DISKBYPATHPATH]:
            blocks.extend(os.listdir(path))

        return blocks
