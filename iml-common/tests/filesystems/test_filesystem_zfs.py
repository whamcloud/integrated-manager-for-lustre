import mock

from iml_common.filesystems.filesystem_zfs import FileSystemZfs
from iml_common.blockdevices.blockdevice_zfs import BlockDeviceZfs
from iml_common.test.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand


class TestFileSystemZFS(CommandCaptureTestCase):
    def setUp(self):
        super(TestFileSystemZFS, self).setUp()

        self.uuid_prop_mock = mock.PropertyMock(return_value="123456789123")
        self.uuid_patcher = mock.patch.object(BlockDeviceZfs, "uuid", self.uuid_prop_mock)
        self.uuid_patcher.start()

        self.type_prop_mock = mock.PropertyMock(return_value="zfs")
        self.type_patcher = mock.patch.object(BlockDeviceZfs, "filesystem_type", self.type_prop_mock)
        self.type_patcher.start()

        self.patch_init_modules = mock.patch.object(BlockDeviceZfs, "_check_module")
        self.patch_init_modules.start()

        self.filesystem = FileSystemZfs("zfs", "zpool1")

        self.addCleanup(mock.patch.stopall)

    def test_mkfs_options(self):
        self.assertEqual([], self.filesystem.mkfs_options(None))

    def test_devices_match(self):
        self.uuid_patcher.stop()
        self.type_patcher.stop()

        self.add_commands(
            CommandCaptureCommand(("zfs", "get", "-H", "-o", "value", "guid", "zpool1"), stdout="123456789123\n")
        )

        self.assertTrue(self.filesystem.devices_match("zpool1", "zpool1", "123456789123"))

        self.assertRanAllCommandsInOrder()

    def test_mkfs_no_options(self):
        """
        Check --mkfsoptions are added to list of parameters provided to mkfs.lustre command when no parameters
        have been provided.
        """
        self.add_commands(
            CommandCaptureCommand(("zpool", "set", "failmode=panic", "zpool1")),
            CommandCaptureCommand(("mkfs.lustre", '--mkfsoptions="mountpoint=none"', "zpool1/MGS")),
        )

        self.assertEqual(
            self.filesystem.mkfs("MGS", self.filesystem.mkfs_options(None)),
            {"uuid": "123456789123", "filesystem_type": "zfs", "inode_size": None, "inode_count": None},
        )

        self.assertRanAllCommandsInOrder()

        self.uuid_prop_mock.assert_called_once()
        self.type_prop_mock.assert_called_once()

    def test_mkfs_no_mkfsoptions(self):
        """
        Check --mkfsoptions are added to list of parameters provided to mkfs.lustre command when some parameters have
        been provided.
        """
        self.add_commands(
            CommandCaptureCommand(("zpool", "set", "failmode=panic", "zpool1")),
            CommandCaptureCommand(
                ("mkfs.lustre", "--mgs", "--backfstype=zfs", '--mkfsoptions="mountpoint=none"', "zpool1/MGS")
            ),
        )

        mkfs_options = ["--mgs", "--backfstype=zfs"]

        self.assertEqual(
            self.filesystem.mkfs("MGS", mkfs_options),
            {"uuid": "123456789123", "filesystem_type": "zfs", "inode_size": None, "inode_count": None},
        )

        self.assertRanAllCommandsInOrder()

        self.uuid_prop_mock.assert_called_once()
        self.type_prop_mock.assert_called_once()

    def test_mkfs_no_mountpoint_option(self):
        """
        Check mountpoint is added to --mkfsoptions when parameter has been provided without mountpoint property
        assignment.
        """
        self.add_commands(
            CommandCaptureCommand(("zpool", "set", "failmode=panic", "zpool1")),
            CommandCaptureCommand(
                (
                    "mkfs.lustre",
                    "--mgs",
                    "--backfstype=zfs",
                    '--mkfsoptions="utf8only=on -o mountpoint=none"',
                    "zpool1/MGS",
                )
            ),
        )

        mkfs_options = ["--mgs", "--backfstype=zfs", '--mkfsoptions="utf8only=on"']

        self.assertEqual(
            self.filesystem.mkfs("MGS", mkfs_options),
            {"uuid": "123456789123", "filesystem_type": "zfs", "inode_size": None, "inode_count": None},
        )

        self.assertRanAllCommandsInOrder()

        self.uuid_prop_mock.assert_called_once()
        self.type_prop_mock.assert_called_once()

    def test_mkfs_multiple_mkfsoptions_no_mountpoint(self):
        """
        Check mountpoint is added to --mkfsoptions when parameter has been provided without mountpoint property
        assignment but with multiple other options.
        """
        self.add_commands(
            CommandCaptureCommand(("zpool", "set", "failmode=panic", "zpool1")),
            CommandCaptureCommand(
                (
                    "mkfs.lustre",
                    "--mgs",
                    "--backfstype=zfs",
                    '--mkfsoptions="listsnapshots=on -o utf8only=on -o mountpoint=none"',
                    "zpool1/MGS",
                )
            ),
        )

        mkfs_options = ["--mgs", "--backfstype=zfs", '--mkfsoptions="listsnapshots=on -o utf8only=on"']

        self.assertEqual(
            self.filesystem.mkfs("MGS", mkfs_options),
            {"uuid": "123456789123", "filesystem_type": "zfs", "inode_size": None, "inode_count": None},
        )

        self.assertRanAllCommandsInOrder()

        self.uuid_prop_mock.assert_called_once()
        self.type_prop_mock.assert_called_once()

    def test_mkfs_multiple_mkfsoptions_with_mountpoint(self):
        """
        Check mountpoint setting is overwritten in --mkfsoptions when parameter has been provided with
        mountpoint property assignment and multiple other options.
        """
        self.add_commands(
            CommandCaptureCommand(("zpool", "set", "failmode=panic", "zpool1")),
            CommandCaptureCommand(
                (
                    "mkfs.lustre",
                    "--mgs",
                    "--backfstype=zfs",
                    '--mkfsoptions="listsnapshots=on -o utf8only=on -o mountpoint=none"',
                    "zpool1/MGS",
                )
            ),
        )

        mkfs_options = [
            "--mgs",
            "--backfstype=zfs",
            '--mkfsoptions="listsnapshots=on -o mountpoint=zpool1/MGS -o utf8only=on"',
        ]

        self.assertEqual(
            self.filesystem.mkfs("MGS", mkfs_options),
            {"uuid": "123456789123", "filesystem_type": "zfs", "inode_size": None, "inode_count": None},
        )

        self.assertRanAllCommandsInOrder()

        self.uuid_prop_mock.assert_called_once()
        self.type_prop_mock.assert_called_once()
