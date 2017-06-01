# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


class LocalFilesystems(object):
    """ Reads /proc/mounts and /etc/fstab to generate a map of block devices occupied by local filesystems """

    def __init__(self, block_devices):
        from chroma_agent.utils import Fstab, Mounts
        fstab = Fstab()
        mounts = Mounts()
        from itertools import chain
        bdev_to_local_fs = {}
        for devpath, mntpnt, fstype in chain(fstab.all(), mounts.all()):
            major_minor = block_devices.path_to_major_minor(devpath)
            if major_minor and fstype != 'lustre' and major_minor in block_devices.block_device_nodes:
                bdev_to_local_fs[major_minor] = (mntpnt, fstype)

        self.bdev_to_local_fs = bdev_to_local_fs

    def all(self):
        return self.bdev_to_local_fs
