# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import re
import os

from testconfig import config
import platform

from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


class TestBlockDeviceZfs(TestBlockDevice):
    _supported_device_types = ['zfs']

    def __init__(self, device_type, device_path):
        super(TestBlockDeviceZfs, self).__init__(device_type, device_path)

        self.device_path_is_zpool_name = not device_path.startswith('/')

    @property
    def preferred_fstype(self):
        return 'zfs'

    # Use this opportunity to disable zfs.target to stop auto import as well.
    @property
    def prepare_device_commands(self):
        return ["systemctl disable zfs.target",
                "zpool create -f %s -o cachefile=none -o multihost=on %s" % (self.device_path, self._device_path)]

    @property
    def device_path(self):
        if self.device_path_is_zpool_name:
            return self._device_path
        else:
            basename = os.path.basename(self._device_path)
            return "zfs_pool_%s" % "".join([c for c in basename if re.match(r'\w', c)])

    @classmethod
    def clear_device_commands(cls, device_paths):
        return ["if zpool list {0}; then zpool destroy -f {0}; zpool labelclear -f {0}; else exit 0; fi".format(
            TestBlockDeviceZfs('zfs', device_path).device_path) for device_path in device_paths]

    @property
    def install_packages_commands(self):
        installer_path = config.get('installer_path', '/tmp')
        return ["flock -x /var/lock/lustre_installer_lock -c 'rpm -q zfs || (cd %s && tar zxf lustre-zfs-%s-installer.tar.gz && cd lustre-zfs && ./install > /tmp/zfs_installer.stdout)'" % (installer_path, "el" + platform.dist()[1][0:1]),
                "modprobe zfs"]

    @property
    def remove_packages_commands(self):
        return ["yum remove -y zfs libzfs2 zfs-dkms spl lustre-osd-zfs*",
                "if [ -e /etc/zfs ]; then rm -rf /etc/zfs; else exit 0; fi"]

    @property
    def release_commands(self):
        # For test we want to export, which is not a risk-free operation
        # but between tests we want to reset
        return ["zpool export %s" % self.device_path]

    @property
    def capture_commands(self):
        # For test we want to import, which is not a risk-free operation
        # but between tests we want to reset
        # partprobe always exits 1 so smother then return
        return ["partprobe | true",
                "udevadm settle",
                "zpool import %s" % self.device_path]

    @classmethod
    def list_devices_commands(cls):
        return['zfs list -H -o name']

    @classmethod
    def zfs_install_commands(cls):
        return ['modprobe zfs']

    @property
    def destroy_commands(self):
        if '/' in self.device_path:
            return ['zfs destroy %s' % self.device_path]

        return ['zpool destroy %s' % self.device_path]

    @property
    def clear_label_commands(self):
        return ['zpool labelclear -f %s' % self.device_path]

    def __str__(self):
        return 'zpool(%s)' % self.device_path
