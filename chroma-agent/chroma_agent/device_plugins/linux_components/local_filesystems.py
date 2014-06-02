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

from chroma_agent.device_plugins.linux_components.device_helper import DeviceHelper


class LocalFilesystems(DeviceHelper):
    """Reads /proc/mounts and /etc/fstab to generate a map of block devices
    occupied by local filesystems"""

    def __init__(self, block_devices):
        from chroma_agent.utils import Fstab, Mounts
        fstab = Fstab()
        mounts = Mounts()
        from itertools import chain
        bdev_to_local_fs = {}
        for dev, mntpnt, fstype in chain(fstab.all(), mounts.all()):
            major_minor = self._dev_major_minor(dev)
            if major_minor and fstype != 'lustre' and major_minor in block_devices.block_device_nodes:
                bdev_to_local_fs[major_minor] = (mntpnt, fstype)

        self.bdev_to_local_fs = bdev_to_local_fs

    def all(self):
        return self.bdev_to_local_fs
