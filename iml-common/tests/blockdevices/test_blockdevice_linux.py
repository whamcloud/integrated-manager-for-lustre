import mock

from iml_common.blockdevices.blockdevice_linux import BlockDeviceLinux
from tests.blockdevices.blockdevice_base_tests import BaseTestBD
from iml_common.test.command_capture_testcase import CommandCaptureCommand


class TestBlockDeviceLinux(BaseTestBD.BaseTestBlockDevice):
    def setUp(self):
        super(TestBlockDeviceLinux, self).setUp()

        self.patch_init_modules = mock.patch.object(BlockDeviceLinux, "_check_module")
        self.patch_init_modules.start()

        self.blockdevice = BlockDeviceLinux("linux", "/dev/sda1")

        self.addCleanup(mock.patch.stopall)

    def test_check_module(self):
        self.patch_init_modules.stop()

        self.add_commands(CommandCaptureCommand(("/usr/sbin/udevadm", "info", "--path=/module/ldiskfs")))

        self.blockdevice._check_module()

        self.assertRanAllCommandsInOrder()

    def test_filesystem_type_unoccupied(self):
        self.add_command(("blkid", "-p", "-o", "value", "-s", "TYPE", self.blockdevice._device_path))

        self.assertEqual(None, self.blockdevice.filesystem_type)
        self.assertRanAllCommandsInOrder()

    def test_filesystem_type_occupied(self):
        self.add_command(("blkid", "-p", "-o", "value", "-s", "TYPE", self.blockdevice._device_path), stdout="ext3")

        self.assertEqual("ext3", self.blockdevice.filesystem_type)
        self.assertRanAllCommandsInOrder()

    def test_filesystem_info_unoccupied(self):
        self.add_command(("blkid", "-p", "-o", "value", "-s", "TYPE", self.blockdevice._device_path))

        self.assertEqual(None, self.blockdevice.filesystem_info)
        self.assertRanAllCommandsInOrder()

    def test_filesystem_info_occupied(self):
        self.add_command(("blkid", "-p", "-o", "value", "-s", "TYPE", self.blockdevice._device_path), stdout="ext3")

        self.assertEqual("Filesystem found: type 'ext3'", self.blockdevice.filesystem_info)
        self.assertRanAllCommandsInOrder()

    def test_uuid(self):
        self.add_command(("blkid", "-p", "-o", "value", "-s", "UUID", self.blockdevice._device_path))

        self.assertEqual(None, self.blockdevice.uuid)
        self.assertRanAllCommandsInOrder()

    def test_preferred_fstype(self):
        self.assertEqual("ldiskfs", self.blockdevice.preferred_fstype)

    def test_device_type(self):
        self.assertEqual("linux", self.blockdevice.device_type)

    def test_device_path(self):
        self.assertEqual("/dev/sda1", self.blockdevice._device_path)

    def test_mgs_targets(self):
        # TODO: implement test
        pass

    def test_property_values(self):
        # TODO: implement test
        pass

    def test_targets(self):
        # TODO: implement test
        pass
