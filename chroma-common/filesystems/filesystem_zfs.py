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


from ..lib.shell import Shell
from filesystem import FileSystem
from ..blockdevices.blockdevice_zfs import BlockDeviceZfs


class FileSystemZfs(FileSystem):
    _supported_filesystems = ['zfs']

    @property
    def label(self):
        block_device = BlockDeviceZfs('zfs', self._device_path)
        return block_device.zfs_properties()['lustre:svname']

    @property
    def inode_size(self):
        return 0

    @property
    def inode_count(self):
        return 0

    def mount_path(self, target_name):
        return "%s/%s" % (self._device_path, target_name)

    def mkfs(self, target_name, options):
        Shell.try_run(["mkfs.lustre"] + options + [self._device_path])

    def mkfs_options(self, target):
        return []
