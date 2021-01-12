import mock

from emf_common.test.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand
from emf_common.filesystems.filesystem_ldiskfs import FileSystemLdiskfs
from emf_common.blockdevices.blockdevice_linux import BlockDeviceLinux
from tests.data import example_data


class TestFileSystemLdiskfs(CommandCaptureTestCase):
    def setUp(self):
        super(TestFileSystemLdiskfs, self).setUp()

        self.uuid_prop_mock = mock.PropertyMock(return_value="123456789123")
        mock.patch.object(BlockDeviceLinux, "uuid", self.uuid_prop_mock).start()

        self.type_prop_mock = mock.PropertyMock(return_value="ldiskfs")
        mock.patch.object(BlockDeviceLinux, "filesystem_type", self.type_prop_mock).start()

        self.patch_init_modules = mock.patch.object(FileSystemLdiskfs, "_check_module")
        self.patch_init_modules.start()

        self.filesystem = FileSystemLdiskfs("ldiskfs", "/dev/sda1")

        self.addCleanup(mock.patch.stopall)

    def test_check_module(self):
        self.patch_init_modules.stop()

        self.add_commands(CommandCaptureCommand(("/usr/sbin/udevadm", "info", "--path=/module/ldiskfs")))

        self.filesystem._check_module()

        self.assertRanAllCommandsInOrder()

    def _mount_fail_initial(self, fail_code):
        """ Test when initial mount fails, retry succeeds and result returned """
        self.add_commands(
            CommandCaptureCommand(
                ("mount", "-t", "lustre", "/dev/sda1", "/mnt/OST0000"), rc=fail_code, executions_remaining=1
            ),
            CommandCaptureCommand(("mount", "-t", "lustre", "/dev/sda1", "/mnt/OST0000"), rc=0, executions_remaining=1),
        )

        self.filesystem.mount("/mnt/OST0000")

        self.assertRanAllCommandsInOrder()

    def test_mount_fail_initial_5(self):
        self._mount_fail_initial(5)

    def test_mount_fail_initial_108(self):
        self._mount_fail_initial(108)

    def test_mount_fail_initial_2(self):
        self._mount_fail_initial(2)

    def test_mount_different_rc_fail_initial(self):
        """ Test when initial mount fails and the rc doesn't cause a retry, exception is raised """
        self.add_commands(
            CommandCaptureCommand(("mount", "-t", "lustre", "/dev/sda1", "/mnt/OST0000"), rc=1, executions_remaining=1)
        )

        self.assertRaises(RuntimeError, self.filesystem.mount, "/mnt/OST0000")

        self.assertRanAllCommandsInOrder()

    def test_mount_fail_second(self):
        """ Test when initial mount fails and the retry fails, exception is raised """
        self.add_commands(
            CommandCaptureCommand(("mount", "-t", "lustre", "/dev/sda1", "/mnt/OST0000"), rc=5, executions_remaining=1),
            CommandCaptureCommand(("mount", "-t", "lustre", "/dev/sda1", "/mnt/OST0000"), rc=5, executions_remaining=1),
        )

        self.assertRaises(RuntimeError, self.filesystem.mount, "/mnt/OST0000")

        self.assertRanAllCommandsInOrder()

    def test_mkfs_options(self):
        test_target = mock.Mock()
        test_target.inode_size = 512
        test_target.bytes_per_inode = 256
        test_target.inode_count = 1024

        self.assertEqual(["-I 512", "-i 256", "-N 1024"], self.filesystem.mkfs_options(test_target))

    def test_devices_match(self):
        mock_stat = mock.patch("os.stat").start()
        self.filesystem.devices_match("/dev/sda1", "/dev/disk/by-id/link_to_sda1", "123456789123")

        mock_stat.assert_has_calls([mock.call("/dev/sda1"), mock.call("/dev/disk/by-id/link_to_sda1")])

    def test_mkfs(self):
        """ Test returning the correct parameters from mkfs call. Test also partly covers inode methods """
        self.add_commands(
            CommandCaptureCommand(("mkfs.lustre", "/dev/sda1")),
            CommandCaptureCommand(
                ("dumpe2fs", "-h", self.filesystem._device_path), stdout=example_data.dumpe2fs_example_output
            ),
            CommandCaptureCommand(
                ("dumpe2fs", "-h", self.filesystem._device_path), stdout=example_data.dumpe2fs_example_output
            ),
        )

        self.assertEqual(
            self.filesystem.mkfs(None, []),
            {"uuid": "123456789123", "filesystem_type": "ldiskfs", "inode_size": 128, "inode_count": 128016},
        )

        self.assertRanAllCommandsInOrder()
