import os
from mock import patch

from tests.command_capture_testcase import CommandCaptureTestCase


class TestClientMountManagement(CommandCaptureTestCase):
    def setUp(self):
        super(TestClientMountManagement, self).setUp()

        client_root = '/mnt/lustre_clients'
        self.client_root = client_root
        self.fsname = 'foobar'
        self.mountspec = '1.2.3.4@tcp:/%s' % self.fsname
        self.mountpoint = os.path.join(client_root, self.fsname)

    def test_mount_lustre_filesystem(self):
        from chroma_agent.action_plugins.manage_client_mounts import mount_lustre_filesystem

        with patch('os.makedirs') as makedirs:
            mount_lustre_filesystem(self.mountspec, self.mountpoint)
            makedirs.assert_called_with(self.mountpoint, 0755)

        self.assertRan(['/sbin/mount.lustre', self.mountspec, self.mountpoint])

    def test_mount_lustre_filesystems(self):
        from chroma_agent.action_plugins.manage_client_mounts import mount_lustre_filesystems

        with patch('chroma_agent.action_plugins.manage_client_mounts.mount_lustre_filesystem') as mlf:
            mount_lustre_filesystems([(self.mountspec, self.mountpoint)])
            mlf.assert_called_with(self.mountspec, self.mountpoint)

    def test_unmount_lustre_filesystem(self):
        from chroma_agent.action_plugins.manage_client_mounts import unmount_lustre_filesystem

        unmount_lustre_filesystem(self.mountspec, self.mountpoint)

        self.assertRan(['/bin/umount', self.mountpoint])

    def test_unmount_lustre_filesystems(self):
        from chroma_agent.action_plugins.manage_client_mounts import unmount_lustre_filesystems

        with patch('chroma_agent.action_plugins.manage_client_mounts.unmount_lustre_filesystem') as ulf:
            unmount_lustre_filesystems([(self.mountspec, self.mountpoint)])
            ulf.assert_called_with(self.mountspec, self.mountpoint)
