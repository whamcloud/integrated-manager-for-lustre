from emf_common.blockdevices.blockdevice_lvm_volume import BlockDeviceLvmVolume
from emf_common.test.command_capture_testcase import CommandCaptureTestCase


class TestBlockDeviceLvmVolume(CommandCaptureTestCase):
    def setUp(self):
        super(TestBlockDeviceLvmVolume, self).setUp()

        self.blockdevice = BlockDeviceLvmVolume("lvm_volume", "/dev/mappper/lvg-test-lvm-test")

    def test_uuid(self):
        self.add_command(
            ("lvs", "--noheadings", "-o", "lv_uuid", "/dev/mappper/lvg-test-lvm-test"),
            stdout="  CtSfyh-ThdO-Bg3i-EiKU-6knJ-Ix4D-ru49Py\n",
        )

        self.assertEqual("CtSfyh-ThdO-Bg3i-EiKU-6knJ-Ix4D-ru49Py", self.blockdevice.uuid)
