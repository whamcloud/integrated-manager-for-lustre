#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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
import re

from ..lib.shell import Shell
from filesystem import FileSystem


class FileSystemLdiskfs(FileSystem):
    # Lustre 2.x's ldiskfs filesystems appear as ext4, maybe we should translate that
    # in the read from blkid. But listing both is safe.
    _supported_filesystems = ['ldiskfs', 'ext4']

    def __init__(self, fstype, device_path):
        super(FileSystemLdiskfs, self).__init__(fstype, device_path)

        self._modules_initialized = False

    def _initialize_modules(self):
        if not self._modules_initialized:
            try:
                # osd_ldiskfs will load ldiskfs in Lustre 2.4.0+
                Shell.try_run(['modprobe', 'osd_ldiskfs'])  # TEI-469: Race loading the osd module during mkfs.lustre
            except Shell.CommandExecutionError:
                Shell.try_run(['modprobe', 'ldiskfs'])      # TEI-469: Race loading the ldiskfs module during mkfs.lustre

            self._modules_initialized = True

    @property
    def label(self):
        self._initialize_modules()

        blkid_output = Shell.try_run(['blkid', '-c/dev/null', '-o', 'value', '-s', 'LABEL', self._device_path])

        return blkid_output.strip()

    @property
    def inode_size(self):
        self._initialize_modules()

        dumpe2fs_output = Shell.try_run(['dumpe2fs', '-h', self._device_path])

        return int(re.search("Inode size:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    @property
    def inode_count(self):
        self._initialize_modules()

        dumpe2fs_output = Shell.try_run(["dumpe2fs", "-h", self._device_path])

        return int(re.search("Inode count:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    def mount(self, target_name, mount_point):
        self._initialize_modules()

        result = Shell.run(['mount', '-t', 'lustre', self.mount_path(target_name), mount_point])

        if result.rc == 5:
            # HYD-1040: Sometimes we should retry on a failed registration
            result = Shell.run(['mount', '-t', 'lustre', self.mount_path(target_name), mount_point])

        if result.rc != 0:
            raise RuntimeError("Error (%s) mounting '%s': '%s' '%s'" % (result.rc, mount_point, result.stdout, result.stderr))

    # A curiosity with lustre on ldiskfs is that the umount must be on the 'realpath' not the path that was mkfs'd/mounted
    def umount(self, target_name, mount_point):
        return Shell.try_run(["umount", os.path.realpath(self._device_path)])

    def mkfs(self, target_name, options):
        self._initialize_modules()

        Shell.try_run(['mkfs.lustre'] + options + [self._device_path])

    def mkfs_options(self, target):
        mkfsoptions = []

        if target.inode_size:
            mkfsoptions.append("-I %s" % target.inode_size)
        if target.bytes_per_inode:
            mkfsoptions.append("-i %s" % target.bytes_per_inode)
        if target.inode_count:
            mkfsoptions.append("-N %s" % target.inode_count)

        return mkfsoptions
