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


class TestBlockDeviceLvm(TestBlockDevice):
    _supported_device_types = ['lvm']

    def __init__(self, device_type, device_path):
        super(TestBlockDeviceLvm, self).__init__(device_type, device_path)

    @property
    def preferred_fstype(self):
        return 'ldiskfs'

    # Create a lvm on the device.
    @property
    def prepare_device_commands(self):
        return ["vgcreate %s %s; lvcreate --wipesignatures n -l 100%%FREE --name %s %s" % (self.vg_name,
                                                                                           self._device_path,
                                                                                           self.lv_name,
                                                                                           self.vg_name)]

    @property
    def vg_name(self):
        return "vg_%s" % "".join([c for c in self._device_path if re.match(r'\w', c)])

    @property
    def lv_name(self):
        return "lv_%s" % "".join([c for c in self._device_path if re.match(r'\w', c)])

    @property
    def device_path(self):
        return "/dev/%s/%s" % (self.vg_name, self.lv_name)

    @classmethod
    def clear_device_commands(cls, device_paths):
        return ["if vgdisplay %s; then vgremove -f %s; else exit 0; fi" % (TestBlockDeviceLvm('lvm', device_path).vg_name,
                                                                           TestBlockDeviceLvm('lvm', device_path).vg_name) for device_path in device_paths]

    @property
    def install_packages_commands(self):
        return []
