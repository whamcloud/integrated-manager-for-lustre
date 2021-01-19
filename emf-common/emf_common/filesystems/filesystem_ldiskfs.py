# Copyright (c) 2021 DDN. All rights reserved.
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
    _supported_filesystems = ["ldiskfs", "ext4"]

    @property
    def label(self):
        self._check_module()

        blkid_output = shell.Shell.try_run(["blkid", "-c/dev/null", "-o", "value", "-s", "LABEL", self._device_path])

        return blkid_output.strip()

    @property
    def inode_size(self):
        self._check_module()

        dumpe2fs_output = shell.Shell.try_run(["dumpe2fs", "-h", self._device_path])

        return int(re.search("Inode size:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    @property
    def inode_count(self):
        self._check_module()

        dumpe2fs_output = shell.Shell.try_run(["dumpe2fs", "-h", self._device_path])

        return int(re.search("Inode count:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    # A curiosity with lustre on ldiskfs is that the umount must be on the 'realpath' not the path that was mkfs'd/mounted
    def umount(self):
        return shell.Shell.try_run(["umount", os.path.realpath(self._device_path)])

    def mkfs(self, target_name, options):
        shell.Shell.try_run(["mkfs.lustre"] + options + [self._device_path])

        return {
            "uuid": self.uuid,
            "filesystem_type": self.filesystem_type,
            "inode_size": self.inode_size,
            "inode_count": self.inode_count,
        }

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
