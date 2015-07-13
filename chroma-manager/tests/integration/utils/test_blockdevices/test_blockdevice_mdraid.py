#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


class TestBlockDeviceMdRaid(TestBlockDevice):
    _supported_device_types = ['mdraid']

    def __init__(self, device_type, device_path):
        super(TestBlockDeviceMdRaid, self).__init__(device_type, device_path)

    @property
    def preferred_fstype(self):
        return 'ldiskfs'

    # Create a mdraid on the device.
    @property
    def prepare_device_commands(self):
        return ["mdadm --zero-superblock %s" % self._device_path,
                "yes | mdadm --create %s --level=1 --raid-disks=2 missing %s" % (self.device_path, self._device_path)]

    @property
    def device_path(self):
        return "/dev/md/%s" % self._device_path[-24:]

    @classmethod
    def clear_device_commands(cls, device_paths):
        return ["if [ -e %s ]; then mdadm --stop %s && mdadm --zero-superblock %s; fi" % (TestBlockDeviceMdRaid('mdraid', device_path).device_path,
                                                                                          TestBlockDeviceMdRaid('mdraid', device_path).device_path,
                                                                                          device_path) for device_path in device_paths]

    @property
    def install_packages_commands(self):
        return ["yum install -y mdadm"]
