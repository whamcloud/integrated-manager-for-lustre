import json

import mock
from chroma_agent.device_plugins.linux import LocalFilesystems
from tests.test_utils import patch_open
from tests.device_plugins.linux.test_linux import MockDmsetupTable, DummyDataTestCase
from tests.command_capture_testcase import CommandCaptureTestCase


class TestNonLocalLvmComponents(DummyDataTestCase):
    def test_HYD_2431(self):
        devices_data = json.loads(self.load('devices_HYD-2431.json'))
        dmsetup_data = self.load('dmsetup_HYD-2431.json')

        actual_lvs = MockDmsetupTable(dmsetup_data, devices_data).lvs
        expected_lvs = json.loads(self.load('lvs_HYD-2431.json'))
        self.assertDictEqual(actual_lvs, expected_lvs)

        actual_vgs = MockDmsetupTable(dmsetup_data, devices_data).vgs
        expected_vgs = json.loads(self.load('vgs_HYD-2431.json'))
        self.assertDictEqual(actual_vgs, expected_vgs)


class TestLocalFilesystem(CommandCaptureTestCase):
    def test_HYD_1968(self):
        """Reproducer for HYD-1968, check that local filesystems are reported correctly even when they are
           specified in fstab by UUID rather than device path"""

        def dev_major_minor(path):
            return {
                   '/dev/mapper/vg_regalmds00-lv_lustre63': "1:2",
                   '/dev/sdb2': "3:4"
            }.get(path, None)

        block_devices = mock.Mock()
        block_devices.block_device_nodes = {
            "1:2": {'major_minor': "1:2",
                    'path': "/dev/mapper/vg_regalmds00-lv_lustre63",
                    'serial_80': None,
                    'serial_83': None,
                    'size': 1234,
                    'filesystem_type': "ext4",
                    'parent': None},
            "3:4": {'major_minor': "1:2",
                    'path': "/dev/sdb2",
                    'serial_80': None,
                    'serial_83': None,
                    'size': 1234,
                    'filesystem_type': "swap",
                    'parent': None},
        }

        self.add_command(("blkid", "-U", "0420214e-b193-49f0-8b40-a04b7baabbbe"), stdout="/dev/sdb2\n")

        with patch_open({
            '/etc/fstab': """/dev/mapper/vg_regalmds00-lv_lustre63 / ext4 defaults 1 1
UUID=0420214e-b193-49f0-8b40-a04b7baabbbe swap swap defaults 0 0
""",
            '/proc/mounts': ""
        }):
            with mock.patch("chroma_agent.device_plugins.linux.DeviceHelper._dev_major_minor", side_effect=dev_major_minor):
                result = LocalFilesystems(block_devices).all()
                self.assertEqual(result, {
                    "1:2": ("/", "ext4"),
                    "3:4": ("swap", 'swap')
                })
