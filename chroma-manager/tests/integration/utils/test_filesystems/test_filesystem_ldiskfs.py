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


from tests.integration.utils.test_filesystems.test_filesystem import TestFileSystem


class TestFileSystemLdiskfs(TestFileSystem):
    _supported_filesystems = ['ldiskfs', 'ext4']

    def __init__(self, fstype, device_path):
        super(TestFileSystemLdiskfs, self).__init__(fstype, device_path)

    def mkfs_command(self, targets, type, fsname, mgs_nids, additional_options):
        return 'mkfs.lustre --backfstype=ldiskfs %s %s %s --fsname=%s %s %s' % (" ".join(additional_options),
                                                                                self._failover_parameter(targets),
                                                                                "--index=%s" % targets.get('index'),
                                                                                fsname,
                                                                                self._mgsnode_parameter(mgs_nids),
                                                                                self._device_path)

    @property
    def mount_path(self):
        return self._device_path
