#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

import re

from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


class TestBlockDeviceZfs(TestBlockDevice):
    _supported_device_types = ['zfs']

    def __init__(self, device_type, device_path):
        super(TestBlockDeviceZfs, self).__init__(device_type, device_path)

    @property
    def preferred_fstype(self):
        return 'zfs'

    # Create a zpool on the device.
    @property
    def prepare_device_commands(self):
        return ["zpool create -f %s %s" % (self.device_path, self._device_path)]

    @property
    def device_path(self):
        return "zfs_pool_%s" % "".join([c for c in self._device_path if re.match(r'\w', c)])

    @classmethod
    def clear_device_commands(cls, device_paths):
        return ["if zpool list %s; then zpool destroy %s; else exit 0; fi" % (TestBlockDeviceZfs('zfs', device_path).device_path,
                                                                              TestBlockDeviceZfs('zfs', device_path).device_path) for device_path in device_paths] + \
               ["yum remove -y zfs spl lustre-osd-zfs*",
                "if [ -e /etc/zfs ]; then rm -rf /etc/zfs; else exit 0; fi"]

    @property
    def install_packages_commands(self):
        return ["yum install -y zfs"]

    @property
    def release_commands(self):
        return ["zpool export %s" % self.device_path]

    @property
    def capture_commands(self):
        return ["partprobe | true",                     # partprobe always exits 1 so smother then return
                "zpool import -f %s" % self.device_path]
