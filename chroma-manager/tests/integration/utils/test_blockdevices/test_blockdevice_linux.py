# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


class TestBlockDeviceLinux(TestBlockDevice):
    _supported_device_types = ['linux']

    def __init__(self, device_type, device_path):
        super(TestBlockDeviceLinux, self).__init__(device_type, device_path)

    @property
    def preferred_fstype(self):
        return 'ldiskfs'

    @property
    def device_path(self):
        return self._device_path

    @property
    def destroy_commands(self):
        # Remove any filesystem signatures on the disk
        return ['wipefs -t zfs %s; sync' % self.device_path, 'dd if=/dev/zero of=%s bs=4k count=1; sync' % self.device_path]

    def __str__(self):
        return '%s' % self.device_path
