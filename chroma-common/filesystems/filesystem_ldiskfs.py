# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import re

from ..lib import shell
from filesystem import FileSystem
from ..blockdevices.blockdevice_linux import BlockDeviceLinux


class FileSystemLdiskfs(FileSystem, BlockDeviceLinux):
    # Lustre 2.x's ldiskfs filesystems appear as ext4, maybe we should translate that
    # in the read from blkid. But listing both is safe.
    _supported_filesystems = ['ldiskfs', 'ext4']

    RC_MOUNT_SUCCESS = 0
    RC_MOUNT_INPUT_OUTPUT_ERROR = 5

    def __init__(self, fstype, device_path):
        super(FileSystemLdiskfs, self).__init__(fstype, device_path)

        self._modules_initialized = False

    @property
    def label(self):
        self._initialize_modules()

        blkid_output = shell.Shell.try_run(['blkid', '-c/dev/null', '-o', 'value', '-s', 'LABEL', self._device_path])

        return blkid_output.strip()

    @property
    def inode_size(self):
        self._initialize_modules()

        dumpe2fs_output = shell.Shell.try_run(['dumpe2fs', '-h', self._device_path])

        return int(re.search("Inode size:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    @property
    def inode_count(self):
        self._initialize_modules()

        dumpe2fs_output = shell.Shell.try_run(["dumpe2fs", "-h", self._device_path])

        return int(re.search("Inode count:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    def mount(self, mount_point):
        self._initialize_modules()

        result = shell.Shell.run(['mount', '-t', 'lustre', self._device_path, mount_point])

        if result.rc == self.RC_MOUNT_INPUT_OUTPUT_ERROR:
            # HYD-1040: Sometimes we should retry on a failed registration
            result = shell.Shell.run(['mount', '-t', 'lustre', self._device_path, mount_point])

        if result.rc != self.RC_MOUNT_SUCCESS:
            raise RuntimeError("Error (%s) mounting '%s': '%s' '%s'" % (result.rc, mount_point, result.stdout, result.stderr))

    # A curiosity with lustre on ldiskfs is that the umount must be on the 'realpath' not the path that was mkfs'd/mounted
    def umount(self):
        return shell.Shell.try_run(["umount", os.path.realpath(self._device_path)])

    def mkfs(self, target_name, options):
        self._initialize_modules()

        shell.Shell.try_run(['mkfs.lustre'] + options + [self._device_path])

        return {'uuid': self.uuid,
                'filesystem_type': self.filesystem_type,
                'inode_size': self.inode_size,
                'inode_count': self.inode_count}

    def mkfs_options(self, target):
        mkfsoptions = []

        if target.inode_size:
            mkfsoptions.append("-I %s" % target.inode_size)
        if target.bytes_per_inode:
            mkfsoptions.append("-i %s" % target.bytes_per_inode)
        if target.inode_count:
            mkfsoptions.append("-N %s" % target.inode_count)

        return mkfsoptions

    def devices_match(self, device1_path, device2_path, device2_uuid):
        """
        Verifies that the devices referenced in the parameters are the same

        :param device1_path: first device string representation
        :param device2_path: second device string representation
        :param device2_uuid: uuid of second device
        :return: return True if both device identifiers reference the same object
        """
        return os.stat(device1_path).st_ino == os.stat(device2_path).st_ino
