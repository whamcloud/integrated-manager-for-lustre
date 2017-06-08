# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
        return BlockDeviceZfs('zfs', self._device_path).zfs_properties(False)['lustre:svname']

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
        """
        Retrieve new target dataset path and pass in call to mkfs.lustre.
        Set failmode to panic for underlying zpool and ensure correct property values set when creating dataset by
        supplying mkfsoptions which are passed to the underlying backfs tools (zfs in this case).

        :param target_name: lustre target name
        :param options: list of options to supply to mkfs command
        :return: dict of new target info
        """
        self._initialize_modules()

        # set 'failmode=panic' property on underlying device (zpool)
        BlockDeviceZfs('zfs', self._device_path).failmode = 'panic'

        new_path = self.mount_path(target_name)

        # set 'mountpoint=none' for created ZfsDatasets
        try:
            options_idx = next(options.index(option) for option in options if '--mkfsoptions=' in option)
        except StopIteration:
            # no mkfsoptions option exists, add one
            options.append('--mkfsoptions="mountpoint=none"')
        else:
            # retrieve list of mkfsoptions from existing parameter string
            mkfsoptions = options[options_idx].split('=', 1)[1].strip('"').split(' -o ')
            try:
                mountpoint_idx = next(mkfsoptions.index(option) for option in mkfsoptions if 'mountpoint=' in option)
            except StopIteration:
                pass
            else:
                # we want to overwrite any existing mountpoint property value, so first remove
                mkfsoptions.pop(mountpoint_idx)

            mkfsoptions.append('mountpoint=none')
            options[options_idx] = '--mkfsoptions="%s"' % ' -o '.join([opt for opt in mkfsoptions])

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
