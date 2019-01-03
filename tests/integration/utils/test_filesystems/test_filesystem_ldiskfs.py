# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from tests.integration.utils.test_filesystems.test_filesystem import TestFileSystem


class TestFileSystemLdiskfs(TestFileSystem):
    _supported_filesystems = ["ldiskfs", "ext4"]

    def __init__(self, fstype, device_path):
        super(TestFileSystemLdiskfs, self).__init__(fstype, device_path)

    def mkfs_command(self, targets, type, fsname, mgs_nids, additional_options):
        return "mkfs.lustre --backfstype=ldiskfs %s %s %s --fsname=%s %s %s" % (
            " ".join(additional_options),
            self._failover_parameter(targets),
            "--index=%s" % targets.get("index"),
            fsname,
            self._mgsnode_parameter(mgs_nids),
            self._device_path,
        )

    @property
    def mount_path(self):
        return self._device_path
