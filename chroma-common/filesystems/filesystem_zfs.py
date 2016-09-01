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


from ..lib import shell
from ..blockdevices.blockdevice_zfs import BlockDeviceZfs
from filesystem import FileSystem


class FileSystemZfs(FileSystem, BlockDeviceZfs):
    _supported_filesystems = ['zfs']

    def __init__(self, fstype, device_path):
        super(FileSystemZfs, self).__init__(fstype, device_path)

        self._modules_initialized = False
        self._zfs_properties = None

    @property
    def label(self):
        return BlockDeviceZfs('zfs', self._device_path).zfs_properties()['lustre:svname']

    @property
    def inode_size(self):
        # TODO: this is knowledge of the subclass specific type in the base class which shouldn't be there
        return None

    @property
    def inode_count(self):
        # TODO: this is knowledge of the subclass specific type in the base class which shouldn't be there
        return None

    def mount_path(self, target_name):
        """
        Before FormatTargetJob, _device_path will reference the zpool, but afterwards
        _device_path will reference the zpool/dataset (after being updated during
        UpdateManagedTargetMount step)

        :param target_name: lustre target name
        :return: lustre target path <zpool>/<dataset>
        """
        return "%s/%s" % (self._device_path, target_name)

    def mkfs(self, target_name, options):
        self._initialize_modules()

        new_path = self.mount_path(target_name)

        shell.Shell.try_run(["mkfs.lustre"] + options + [new_path])

        return {'uuid': BlockDeviceZfs('zfs', new_path).uuid,
                'filesystem_type': self.filesystem_type,
                'inode_size': None,
                'inode_count': None}

    def mkfs_options(self, target):
        return []

    def devices_match(self, device1_path, device2_path, device2_uuid):
        """
        Verifies that the devices referenced in the parameters are the same

        :param device1_path: first device string representation
        :param device2_path: second device string representation
        :param device2_uuid: uuid of second device
        :return: return True if both device identifiers reference the same object
        """
        return device2_uuid == BlockDeviceZfs('zfs', device1_path).uuid
