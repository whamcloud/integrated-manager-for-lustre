# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from tests.integration.utils.test_filesystems.test_filesystem import TestFileSystem


class TestFileSystemZfs(TestFileSystem):
    _supported_filesystems = ["zfs"]

    def __init__(self, fstype, device_path):
        super(TestFileSystemZfs, self).__init__(fstype, device_path)
        self._mount_path = None

    def mkfs_command(self, targets, type, fsname, mgs_nids, additional_options):
        index = targets.get("index")

        self._mount_path = "%s/%s%s" % (self._device_path, type, "_index%s" % index)

        return "mkfs.lustre --backfstype=zfs %s %s %s --fsname=%s %s %s" % (
            " ".join(additional_options),
            self._failover_parameter(targets),
            "--index=%s" % index,
            fsname,
            self._mgsnode_parameter(mgs_nids),
            self.mount_path,
        )

    @property
    def mount_path(self):
        assert self._mount_path, "Mount path unknown"

        return self._mount_path
