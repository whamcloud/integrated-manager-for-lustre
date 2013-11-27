#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


import os
import errno

from chroma_agent import config
from chroma_agent import shell


def _filesystem_mountpoint(mountspec):
    client_root = config.get('settings', 'agent')['lustre_client_root']
    fsname = mountspec.split(':/')[1]
    return os.path.join(client_root, fsname)


def mount_lustre_filesystem(mountspec):
    mountpoint = _filesystem_mountpoint(mountspec)

    try:
        os.makedirs(mountpoint, 0755)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    shell.try_run(['/sbin/mount.lustre', mountspec, mountpoint])


def mount_lustre_filesystems(filesystems):
    for mountspec in filesystems:
        mount_lustre_filesystem(mountspec)


def unmount_lustre_filesystem(mountspec):
    mountpoint = _filesystem_mountpoint(mountspec)

    shell.try_run(['/bin/umount', mountpoint])


def unmount_lustre_filesystems(filesystems):
    for mountspec in filesystems:
        unmount_lustre_filesystem(mountspec)


ACTIONS = [mount_lustre_filesystems, unmount_lustre_filesystems, mount_lustre_filesystem, unmount_lustre_filesystem]
CAPABILITIES = ['manage_client_mounts']
