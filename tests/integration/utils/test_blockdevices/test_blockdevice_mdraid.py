# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


class TestBlockDeviceMdRaid(TestBlockDevice):
    _supported_device_types = ["mdraid"]

    def __init__(self, device_type, device_path):
        super(TestBlockDeviceMdRaid, self).__init__(device_type, device_path)

    @property
    def preferred_fstype(self):
        return "ldiskfs"

    # Create a mdraid on the device.
    @property
    def prepare_device_commands(self):
        return [
            "mdadm --zero-superblock %s" % self._device_path,
            "yes | mdadm --create %s --level=1 --raid-disks=2 missing %s" % (self.device_path, self._device_path),
        ]

    @property
    def device_path(self):
        return "/dev/md/%s" % self._device_path[-24:]

    @classmethod
    def clear_device_commands(cls, device_paths):
        return [
            "if [ -e %s ]; then mdadm --stop %s && mdadm --zero-superblock %s; fi"
            % (
                TestBlockDeviceMdRaid("mdraid", device_path).device_path,
                TestBlockDeviceMdRaid("mdraid", device_path).device_path,
                device_path,
            )
            for device_path in device_paths
        ]

    @property
    def install_packages_commands(self):
        return ["yum install -y mdadm"]
