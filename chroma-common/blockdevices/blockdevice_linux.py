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


from blockdevice import BlockDevice
from ..lib import shell


class BlockDeviceLinux(BlockDevice):
    _supported_device_types = ['linux']

    @property
    def filesystem_type(self):
        rc, blkid_output, blkid_err = shell.run(["blkid", "-p", "-o", "value", "-s", "TYPE", self._device_path])

        if rc == 2:
            # blkid returns 2 if there is no filesystem on the device
            return None
        elif rc == 0:
            filesystem_type = blkid_output.strip()

            if filesystem_type:
                return filesystem_type
            else:
                # Empty filesystem: blkid returns 0 but prints no FS if it seems something non-filesystem-like
                # like an MBR
                return None
        else:
            raise RuntimeError("Unexpected return code %s from blkid %s: '%s' '%s'" % (rc, self._device_path, blkid_output, blkid_err))

    @property
    def uuid(self):
        return shell.try_run(["blkid", "-o", "value", "-s", "UUID", self._device_path]).strip()

    @property
    def preferred_fstype(self):
        return 'ldiskfs'
