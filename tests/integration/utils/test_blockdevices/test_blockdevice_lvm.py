# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import re

from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


class TestBlockDeviceLvm(TestBlockDevice):
    _supported_device_types = ["lvm"]

    def __init__(self, device_type, device_path):
        super(TestBlockDeviceLvm, self).__init__(device_type, device_path)

    @property
    def preferred_fstype(self):
        return "ldiskfs"

    # Create a lvm on the device.
    @property
    def create_device_commands(self):
        # FIXME: the use of --yes in the {vg,lv}create commands is a work-around for #500
        # and should be reverted when #500 is fixed
        return [
            "vgcreate --yes %s %s; lvcreate --yes --wipesignatures n -l 100%%FREE --name %s %s"
            % (self.vg_name, self._device_path, self.lv_name, self.vg_name)
        ]

    @property
    def vg_name(self):
        return "vg_%s" % "".join([c for c in self._device_path if re.match(r"\w", c)])

    @property
    def lv_name(self):
        return "lv_%s" % "".join([c for c in self._device_path if re.match(r"\w", c)])

    @property
    def device_path(self):
        return "/dev/%s/%s" % (self.vg_name, self.lv_name)

    @classmethod
    def clear_device_commands(cls, device_paths):
        lv_destroy = [
            "if lvdisplay /dev/{0}/{1}; then lvchange -an /dev/{0}/{1} && lvremove /dev/{0}/{1}; else exit 0; fi".format(
                TestBlockDeviceLvm("lvm", device_path).vg_name, TestBlockDeviceLvm("lvm", device_path).lv_name
            )
            for device_path in device_paths
        ]
        vg_destroy = [
            "if vgdisplay {0}; then vgremove {0}; else exit 0; fi".format(
                TestBlockDeviceLvm("lvm", device_path).vg_name
            )
            for device_path in device_paths
        ]

        return lv_destroy + vg_destroy

    @property
    def install_packages_commands(self):
        return []
