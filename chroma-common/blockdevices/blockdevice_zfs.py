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

from ..lib import shell
from blockdevice import BlockDevice


class BlockDeviceZfs(BlockDevice):
    _supported_device_types = ['zfs']

    @property
    def filesystem_type(self):
        # We should verify the value, but for now lets just presume.
        return 'zfs'

    @property
    def uuid(self):
        out = shell.try_run(['zfs', 'list', '-o', 'name,guid'])
        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            result = re.search("^%s\s+(.+)" % self._device_path, line)
            if (result):
                return result.group(1)

        raise RuntimeError("Unabled to find UUID for device %s" % self._device_path)

    @property
    def preferred_fstype(self):
        return 'zfs'
