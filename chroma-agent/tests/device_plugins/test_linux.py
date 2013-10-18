import json
import mock
import os
from django.utils import unittest
from chroma_agent.device_plugins.linux import DmsetupTable, LocalFilesystems, MdRaid
from tests.test_utils import patch_open, patch_run


class MockDmsetupTable(DmsetupTable):
    def __init__(self, dmsetup_data, devices_data):
        self.lvs = devices_data['lvs']
        self.vgs = devices_data['vgs']
        self.mpaths = {}
        self.block_devices = mock.Mock()
        self.block_devices.node_block_devices = devices_data['node_block_devices']
        self.block_devices.block_device_nodes = devices_data['block_device_nodes']
        self._parse_dm_table(dmsetup_data)


class DummyDataTestCase(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/device_plugins/linux")

    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()


class TestDmSetupParse(DummyDataTestCase):
    def test_dmsetup_table(self):
        """This is a regression test using data from a test/dev machine which includes LVs and multipath, all the data
           is just as it is when run through on Chroma 1.0.0.0: this really is a *regression* test rather than
           a correctness test.  The system from which this data was gathered ran CentOS 5.6"""
        self._test_dmsetup('devices_1.txt', 'dmsetup_1.txt', 'mpaths_1.txt')

    def _test_dmsetup(self, devices_filename, dmsetup_filename, mpaths_filename):
        devices_data = json.loads(self.load(devices_filename))
        dmsetup_data = self.load(dmsetup_filename)
        actual_mpaths = MockDmsetupTable(dmsetup_data, devices_data).mpaths
        expected_mpaths = json.loads(self.load(mpaths_filename))

        self.assertDictEqual(actual_mpaths, expected_mpaths)

    def test_HYD_1383(self):
        """Minimal reproducer for HYD-1383.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
           let it run through far enough to experience failure."""
        self._test_dmsetup('devices_NTAP-12-min.txt', 'dmsetup_NTAP-12-min.txt', 'mpaths_NTAP-12-min.txt')

    def test_HYD_1385(self):
        """Minimal reproducer for HYD-1385.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
           let it run through far enough to experience failure."""
        self._test_dmsetup('devices_HYD-1385.txt', 'dmsetup_HYD-1385.txt', 'mpaths_HYD-1385.txt')

    def test_HYD_1390(self):
        """Minimal reproducer for HYD-1385.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
           let it run through far enough to experience failure."""
        self._test_dmsetup('devices_HYD-1390.txt', 'dmsetup_HYD-1390.txt', 'mpaths_HYD-1390.txt')


class TestNonLocalLvmComponents(DummyDataTestCase):
    def test_HYD_2431(self):
        devices_data = json.loads(self.load('devices_HYD-2431.txt'))
        dmsetup_data = self.load('dmsetup_HYD-2431.txt')

        actual_lvs = MockDmsetupTable(dmsetup_data, devices_data).lvs
        expected_lvs = json.loads(self.load('lvs_HYD-2431.txt'))
        self.assertDictEqual(actual_lvs, expected_lvs)

        actual_vgs = MockDmsetupTable(dmsetup_data, devices_data).vgs
        expected_vgs = json.loads(self.load('vgs_HYD-2431.txt'))
        self.assertDictEqual(actual_vgs, expected_vgs)


class TestLocalFilesystem(unittest.TestCase):
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

        with patch_open({
            '/etc/fstab': """/dev/mapper/vg_regalmds00-lv_lustre63 / ext4 defaults 1 1
UUID=0420214e-b193-49f0-8b40-a04b7baabbbe swap swap defaults 0 0
""",
            '/proc/mounts': ""
        }):
            with mock.patch("chroma_agent.device_plugins.linux.DeviceHelper._dev_major_minor", side_effect=dev_major_minor):
                with patch_run(["blkid", "-U", "0420214e-b193-49f0-8b40-a04b7baabbbe"], rc=0, stdout="/dev/sdb2\n"):
                    result = LocalFilesystems(block_devices).all()
                    self.assertEqual(result, {
                        "1:2": ("/", "ext4"),
                        "3:4": ("swap", 'swap')
                    })

class TestMDRaid(unittest.TestCase):

    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/device_plugins/linux")

        self.md_value_good = {'mdstat': """Personalities : [raid1]
md127 : active (auto-read-only) raid1 sdc2[1] sdc1[0]
      16056704 blocks super 1.2 [2/2] [UU]

md128 : active (auto-read-only) raid0 sdd[0]
      16056704 blocks super 1.2 [2/2] [UU]

unused devices: <none>\n""",
                              'mdadm': {"/dev/md127": """ARRAY /dev/md127 level=raid1 num-devices=2 metadata=1.2 name=mac-node:1 UUID=15054135:be3426c6:f1387822:49830fb5
   devices=/dev/sdc1,/dev/sdc2\n""",
                                        "/dev/md128": """ARRAY /dev/md128 level=raid0 num-devices=1 metadata=1.2 name=mac-node:1 UUID=15054135:be3426c6:f1387822:49830fb6
   devices=/dev/sdd1\n"""},
                              'results': [{
                                              'uuid': '15054135:be3426c6:f1387822:49830fb5',
                                              'path': '/dev/md127',
                                              'mm': '9:127',
                                              'device_paths': ['/dev/sdc1','/dev/sdc2']
                                          },
                                          {
                                              'uuid': '15054135:be3426c6:f1387822:49830fb6',
                                              'path': '/dev/md128',
                                              'mm': '9:128',
                                              'device_paths': ['/dev/sdd1']
                                          }]
        }

    def _load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def _load_dmsetup(self, devices_filename, dmsetup_filename):
        self.devices_data = json.loads(self._load(devices_filename))
        self.dmsetup_data = self._load(dmsetup_filename)

        return MockDmsetupTable(self.dmsetup_data, self.devices_data)

    def mock_debug(self, value):
        print value

    class mock_open:
        md_value = None

        def __init__(self, fname):
            pass

        def read(self):
            return self.md_value["mdstat"]

    def mock_try_run(self, arg_list):
        return self.md_value["mdadm"][arg_list[4]]

    def mock_dev_major_minor(self, path):
        if (self.devices_data['node_block_devices'].has_key(path)):
            return self.devices_data['node_block_devices'][path]
        else:
            return None

    def _setup_md_raid(self, devices_filename, dmsetup_filename, md_value):
        dm_setup_table = self._load_dmsetup(devices_filename, dmsetup_filename)

        with mock.patch('logging.Logger.debug', self.mock_debug):
            with mock.patch('chroma_agent.shell.try_run', self.mock_try_run):
                with mock.patch('__builtin__.open', self.mock_open):
                    with mock.patch('chroma_agent.device_plugins.linux.DeviceHelper._dev_major_minor', self.mock_dev_major_minor):

                        self.md_value = md_value
                        self.mock_open.md_value = md_value

                        return MdRaid(dm_setup_table.block_devices).all()

    def test_mdraid_pass(self):
        mds = self._setup_md_raid('devices_MdRaid.txt', 'dmsetup_MdRaid.txt', self.md_value_good)

        self.assertTrue(len(mds) == len(self.md_value_good['results']))

        for value in self.md_value_good['results']:
            uuid = value['uuid']

            self.assertTrue(mds.has_key(uuid))
            self.assertTrue(mds[uuid]['path'] == value['path'])
            self.assertTrue(mds[uuid]['block_device'] == value['mm'])
            self.assertTrue(len(mds[uuid]['drives']) == len(value['device_paths']))
            for i in range(0, len(value['device_paths'])):
                self.assertTrue(mds[uuid]['drives'][i] == self.mock_dev_major_minor(value['device_paths'][i]))

    # This should not fail as such, but the dmsetup data doesn't contain the device info for the md device so the
    # data is inconsistent. The code should deal with this and return an mddevice with empty drives..
    def test_mdraid_fail(self):
        mds = self._setup_md_raid('devices_HYD-1385.txt', 'dmsetup_HYD-1385.txt', self.md_value_good)

        # No data should come back
        self.assertTrue(len(mds) == 0)

