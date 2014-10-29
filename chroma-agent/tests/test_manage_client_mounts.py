import os
from StringIO import StringIO
from mock import patch, mock_open

from tests.command_capture_testcase import CommandCaptureTestCase


class TestClientMountManagement(CommandCaptureTestCase):
    def setUp(self):
        super(TestClientMountManagement, self).setUp()

        client_root = '/mnt/lustre_clients'
        self.client_root = client_root
        self.fsname = 'foobar'
        self.mountspec = '1.2.3.4@tcp:/%s' % self.fsname
        self.mountpoint = os.path.join(client_root, self.fsname)

    @patch('chroma_agent.action_plugins.manage_client_mounts.delete_fstab_entry')
    @patch('chroma_agent.action_plugins.manage_client_mounts.create_fstab_entry')
    def test_mount_lustre_filesystem(self, create, delete):
        self.results = {('/bin/mount', '/mnt/lustre_clients/foobar'): (0, "", "")}

        from chroma_agent.action_plugins.manage_client_mounts import mount_lustre_filesystem

        with patch('os.makedirs') as makedirs:
            mount_lustre_filesystem(self.mountspec, self.mountpoint)
            makedirs.assert_called_with(self.mountpoint, 0755)

        self.assertRan(['/bin/mount', self.mountpoint])
        create.assert_called_with(self.mountspec, self.mountpoint)

    @patch('chroma_agent.action_plugins.manage_client_mounts.delete_fstab_entry')
    @patch('chroma_agent.action_plugins.manage_client_mounts.create_fstab_entry')
    def test_mount_lustre_filesystems(self, *patches):
        from chroma_agent.action_plugins.manage_client_mounts import mount_lustre_filesystems

        with patch('chroma_agent.action_plugins.manage_client_mounts.mount_lustre_filesystem') as mlf:
            mount_lustre_filesystems([(self.mountspec, self.mountpoint)])
            mlf.assert_called_with(self.mountspec, self.mountpoint)

    @patch('chroma_agent.action_plugins.manage_client_mounts.delete_fstab_entry')
    def test_unmount_lustre_filesystem(self, *patches):
        self.results = {('/bin/umount', '/mnt/lustre_clients/foobar'): (0, "", "")}

        from chroma_agent.action_plugins.manage_client_mounts import unmount_lustre_filesystem

        unmount_lustre_filesystem(self.mountspec, self.mountpoint)

        self.assertRan(['/bin/umount', self.mountpoint])

    @patch('chroma_agent.action_plugins.manage_client_mounts.delete_fstab_entry')
    def test_unmount_lustre_filesystems(self, *patches):
        from chroma_agent.action_plugins.manage_client_mounts import unmount_lustre_filesystems

        with patch('chroma_agent.action_plugins.manage_client_mounts.unmount_lustre_filesystem') as ulf:
            unmount_lustre_filesystems([(self.mountspec, self.mountpoint)])
            ulf.assert_called_with(self.mountspec, self.mountpoint)

    @patch('chroma_agent.action_plugins.manage_client_mounts.delete_fstab_entry')
    def test_create_fstab_entry(self, delete):
        from chroma_agent.action_plugins.manage_client_mounts import FSTAB_ENTRY_TEMPLATE, create_fstab_entry

        with patch('chroma_agent.action_plugins.manage_client_mounts.open',
                   mock_open(), create=True) as mo:
            create_fstab_entry(self.mountspec, self.mountpoint)
            mo().write.assert_called_once_with(FSTAB_ENTRY_TEMPLATE %
                                               (self.mountspec, self.mountpoint))
        delete.assert_called_with(self.mountspec, self.mountpoint)

    @patch('os.rename')
    def test_delete_fstab_entry(self, rename):
        from chroma_agent.action_plugins.manage_client_mounts import delete_fstab_entry

        fake_fstab = """#
# /etc/fstab
# blah

/dev/foo        /bar        something   defaults    1 1
%(mountspec)s              %(mountpoint)s          lustre      defaults,_netdev    0 0
%(mountspec)s1              %(mountpoint)s1          lustre      defaults,_netdev    0 0

1.2.3.4:/baz    /qux        nfs         defaults    0 0
""" % dict(mountspec = self.mountspec, mountpoint = self.mountpoint)
        data = StringIO(fake_fstab)

        with patch('chroma_agent.action_plugins.manage_client_mounts.open',
                   mock_open(), create=True) as mo:
            mo.return_value.__iter__.return_value = data
            delete_fstab_entry(self.mountspec, self.mountpoint)

            new_fstab = [c[1][0] for c in mo().write.mock_calls]
            self.assertMatchInList(r"^# /etc/fstab", new_fstab)
            self.assertMatchInList(r'^%s1\s' % self.mountspec, new_fstab)
            self.assertNotMatchInList(r'^%s\s' % self.mountspec, new_fstab)
            self.assertMatchInList(r"^1.2.3.4:/baz", new_fstab)
        rename.assert_called_with("/etc/fstab.iml.edit", "/etc/fstab")

    def assertMatchInList(self, pattern, array):
        import re
        if isinstance(pattern, basestring):
            pattern = re.compile(pattern)

        for string in array:
            if re.search(pattern, string):
                return True

        msg = "No matches found: %r not found in list" % pattern.pattern
        raise AssertionError(msg)

    def assertNotMatchInList(self, pattern, array):
        found = False
        try:
            found = self.assertMatchInList(pattern, array)
        except AssertionError:
            pass

        if found:
            msg = "Unexpected match found: %r was found in list" % pattern
            raise AssertionError(msg)

        return True
