import mock

from chroma_agent.chroma_common.filesystems.filesystem_zfs import FileSystemZfs
from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import BlockDeviceZfs
from tests.command_capture_testcase import CommandCaptureTestCase


class TestFileSystemZFS(CommandCaptureTestCase):
    def setUp(self):
        super(TestFileSystemZFS, self).setUp()

        self.uuid_prop_mock = mock.PropertyMock(return_value='123456789123')
        mock.patch.object(BlockDeviceZfs, 'uuid', self.uuid_prop_mock).start()

        self.type_prop_mock = mock.PropertyMock(return_value='zfs')
        mock.patch.object(BlockDeviceZfs, 'filesystem_type', self.type_prop_mock).start()

        self.patch_init_modules = mock.patch.object(FileSystemZfs, '_initialize_modules')
        self.patch_init_modules.start()

        self.filesystem = FileSystemZfs('zfs', 'zpool1')

        self.addCleanup(mock.patch.stopall)

    def test_mkfs_options(self):
        self.assertEqual([], self.filesystem.mkfs_options(None))

    def test_devices_match(self):
        self.assertTrue(self.filesystem.devices_match('zpool1', 'zpool1', '123456789123'))

        self.uuid_prop_mock.assert_called_once()
        self.type_prop_mock.assert_called_once()

    def test_mkfs(self):
        self.add_command(("mkfs.lustre", 'zpool1/MGS'))

        self.assertEqual(self.filesystem.mkfs('MGS', self.filesystem.mkfs_options(None)),
                         {'uuid': '123456789123', 'filesystem_type': 'zfs', 'inode_size': None, 'inode_count': None})

        self.assertRanAllCommandsInOrder()

        self.uuid_prop_mock.assert_called_once()
        self.type_prop_mock.assert_called_once()
