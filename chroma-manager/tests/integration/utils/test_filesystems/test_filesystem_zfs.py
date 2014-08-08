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


class TestFileSystemZfs(TestFileSystem):
    _supported_filesystems = ['zfs']

    def __init__(self, fstype, device_path):
        super(TestFileSystemZfs, self).__init__(fstype, device_path)
        self._mount_path = None

    def mkfs_command(self, type, index, fsname, mgs_ip, additional_options):
        self._mount_path = "%s/%s%s" % (self._device_path,
                                        type,
                                        "_index%s" % index if index is not None else "")

        return 'mkfs.lustre --backfstype=zfs %s %s --fsname=%s %s %s' % (" ".join(additional_options),
                                                                         "--index=%s" % index if index is not None else "",
                                                                         fsname,
                                                                         "--mgsnode=%s@tcp0" % mgs_ip if mgs_ip else "",
                                                                         self.mount_path)

    def install_packages_commands(cls):
        return ["yum install -y lustre-osd-zfs"]

    @property
    def mount_path(self):
        assert self._mount_path, "Mount path unknown"

        return self._mount_path
