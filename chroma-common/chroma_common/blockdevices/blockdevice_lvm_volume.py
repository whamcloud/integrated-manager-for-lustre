# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from blockdevice_linux import BlockDeviceLinux
from ..lib import shell


class BlockDeviceLvmVolume(BlockDeviceLinux):
    _supported_device_types = ['lvm_volume']

    @property
    def uuid(self):
        out = shell.Shell.try_run(["lvs", "--noheadings", "-o", "lv_uuid", self._device_path])

        return out.strip()
