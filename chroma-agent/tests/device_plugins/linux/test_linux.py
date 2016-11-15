import collections
import json
import errno
import mock
import os
from django.utils import unittest

from chroma_agent.device_plugins.linux import DmsetupTable
from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices
import chroma_agent.lib.normalize_device_path as ndp
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand


class MockDmsetupTable(DmsetupTable):
    def __init__(self, dmsetup_data, devices_data):
        self.lvs = devices_data['lvs']
        self.vgs = devices_data['vgs']
        self.mpaths = {}
        with mock.patch('chroma_agent.utils.BlkId', return_value={}):
            with mock.patch('chroma_agent.device_plugins.linux_components.block_devices.BlockDevices._parse_sys_block',
                            return_value=(devices_data['block_device_nodes'], devices_data['node_block_devices'])):
                self.block_devices = BlockDevices()
        self._parse_dm_table(dmsetup_data)


class LinuxAgentTests(unittest.TestCase):
    def setUp(self):
        super(LinuxAgentTests, self).setUp()

        tests = os.path.join(os.path.dirname(__file__), '../../')
        self.test_root = os.path.join(tests, "data/device_plugins/linux")

    def assertNormalizedPaths(self, normalized_values):
        class mock_open:
            def __init__(self, fname):
                pass

            def read(self):
                return "root=/not/a/real/path"

        with mock.patch('__builtin__.open', mock_open):
            for path, normalized_path in normalized_values.items():
                self.assertEqual(normalized_path, ndp.normalized_device_path(path),
                                 "Normalized path failure %s != %s" % (normalized_path, ndp.normalized_device_path(path)))


class DummyDataTestCase(LinuxAgentTests):
    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()


class TestDmSetupParse(DummyDataTestCase):
    def _test_dmsetup(self, devices_filename, dmsetup_filename, mpaths_filename, normalized_paths_filename):
        devices_data = json.loads(self.load(devices_filename))
        dmsetup_data = self.load(dmsetup_filename)
        actual_mpaths = MockDmsetupTable(dmsetup_data, devices_data).mpaths
        expected_mpaths = json.loads(self.load(mpaths_filename))
        expected_normalized_paths = json.loads(self.load(normalized_paths_filename))

        self.assertDictEqual(actual_mpaths, expected_mpaths)
        self.assertNormalizedPaths(expected_normalized_paths)

    def test_dmsetup_table(self):
        """This is a regression test using data from a test/dev machine which includes LVs and multipath, all the data
           is just as it is when run through on Chroma 1.0.0.0: this really is a *regression* test rather than
           a correctness test.  The system from which this data was gathered ran CentOS 5.6"""
        self._test_dmsetup('devices_1.json',
                           'dmsetup_1.json',
                           'mpaths_1.json',
                           'normalized_1.json')

    def test_HYD_1383(self):
        """Minimal reproducer for HYD-1383.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
           let it run through far enough to experience failure."""
        self._test_dmsetup('devices_NTAP-12-min.json',
                           'dmsetup_NTAP-12-min.json',
                           'mpaths_NTAP-12-min.json',
                           'normalized_NTAP-12-min.json')

    def test_HYD_1385(self):
        """Minimal reproducer for HYD-1385.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
           let it run through far enough to experience failure."""
        self._test_dmsetup('devices_HYD-1385.json',
                           'dmsetup_HYD-1385.json',
                           'mpaths_HYD-1385.json',
                           'normalized_HYD-1385.json')

    def test_HYD_1390(self):
        """Minimal reproducer for HYD-1385.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
           let it run through far enough to experience failure."""
        self._test_dmsetup('devices_HYD-1390.json',
                           'dmsetup_HYD-1390.json',
                           'mpaths_HYD-1390.json',
                           'normalized_HYD-1390.json')


class TestBlockDevices(CommandCaptureTestCase):
    def setUp(self):
        super(TestBlockDevices, self).setUp()

        with mock.patch('glob.glob', return_value=[]):
            with mock.patch('chroma_agent.utils.BlkId', return_value={}):
                self.block_devices = BlockDevices()

        mock.patch('os.path.isfile', self.mock_isfile).start()
        self.existing_files = []

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def mock_isfile(self, file):
        return file in self.existing_files

    def test_device_node_versions(self):
        for scsi_id in ["/sbin/scsi_id", "/lib/udev/scsi_id"]:
            # Check runs with correct scsi_id
            self.existing_files = [scsi_id]

            self.reset_command_capture()
            self.add_commands(CommandCaptureCommand(((scsi_id, '-g', '-p', '0x80', '/dev/blop'))),
                              CommandCaptureCommand(((scsi_id, '-g', '-p', '0x83', '/dev/blop'))))

            result = self.block_devices._device_node(1, "/dev/blop", 1, None, '1234')

            self.assertRanAllCommandsInOrder()

            self.assertEqual(result, {'parent': None,
                                      'major_minor': 1,
                                      'serial_83': '',
                                      'serial_80': '',
                                      'path': '/dev/blop',
                                      'filesystem_type': None,
                                      'partition_number': '1234',
                                      'size': 1})


class TestDevMajorMinor(LinuxAgentTests):

    MockDevice = collections.namedtuple('MockDevice', 'st_mode st_rdev')

    mock_devices = {'/dev/disk/by-id/adisk': MockDevice(25008, 6)}

    node_block_devices = {'/dev/disk/by-id/adisk': '12:24'}

    def mock_os_stat(self, path):
        if path in TestDevMajorMinor.mock_devices:
            return TestDevMajorMinor.mock_devices[path]
        else:
            raise OSError(errno.ENOENT, 'No such file or directory.')

    def setUp(self):
        super(TestDevMajorMinor, self).setUp()
        self.stat_patcher = mock.patch('os.stat', self.mock_os_stat)
        self.stat_patcher.start()
        mock.patch('os.minor', lambda st_rdev: st_rdev * 4).start()
        mock.patch('os.major', lambda st_rdev: st_rdev * 2).start()
        mock.patch('stat.S_ISBLK', return_value=True).start()
        mock.patch('chroma_agent.lib.shell.AgentShell.try_run').start()
        mock.patch('chroma_agent.utils.BlkId', return_value={0: {'path': self.mock_devices.keys()[0],
                                                                 'type': 'ext4'}}).start()
        mock.patch('chroma_agent.device_plugins.linux_components.block_devices.BlockDevices._parse_sys_block',
                   return_value=(None, None)).start()
        self.addCleanup(mock.patch.stopall)
        self.block_devices = BlockDevices()
        self.block_devices.non_existent_paths = set([])

    def test_dev_major_minor_path_exists(self):
        """ After a successful attempt, path should be removed from no-retry list """
        path = '/dev/disk/by-id/adisk'
        self.block_devices.non_existent_paths.add(path)
        device = self.block_devices._dev_major_minor(path)
        self.assertNotIn(path, self.block_devices.non_existent_paths)
        self.assertEqual(device, '12:24')

    def test_dev_major_minor_path_doesnt_exist(self):
        """ After un-successful attempts, path should be added to no-retry list """
        path = '/dev/disk/by-id/idontexist'
        device = self.block_devices._dev_major_minor(path)
        self.assertIn(path, self.block_devices.non_existent_paths)
        self.assertEqual(device, None)

    def test_dev_major_minor_path_exists_retries(self):
        """ With existing path, method only calls stat once """
        path = '/dev/disk/by-id/adisk'
        self.stat_patcher.stop()
        mock_stat = mock.patch('os.stat', return_value=TestDevMajorMinor.mock_devices[path]).start()
        self.block_devices._dev_major_minor(path)
        self.assertEqual(mock_stat.call_count, 1)
        self.assertNotIn(path, self.block_devices.non_existent_paths)

    def test_dev_major_minor_path_retry_doesnt_exist_retries(self):
        """
        Test non-existent path retries specified amount, and is subsequently added to the no-retry list.
        On the next attempt with the same path, there should be no retries.
        """
        path = '/dev/disk/by-id/idontexist'
        self.stat_patcher.stop()
        self.assertNotIn(path, self.block_devices.non_existent_paths)
        mock_stat = mock.patch('os.stat').start()
        mock_stat.side_effect = OSError(errno.ENOENT, 'No such file or directory.')
        self.block_devices._dev_major_minor(path)
        self.assertEqual(mock_stat.call_count, BlockDevices.MAXRETRIES)
        self.assertIn(path, self.block_devices.non_existent_paths)
        mock_stat.reset_mock()
        self.block_devices._dev_major_minor(path)
        self.assertEqual(mock_stat.call_count, 1)
        self.assertIn(path, self.block_devices.non_existent_paths)

    def test_paths_to_major_minors_paths_exist(self):
        self.block_devices.node_block_devices = self.node_block_devices
        devices = self.block_devices.paths_to_major_minors(['/dev/disk/by-id/adisk'])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices, ['12:24'])

    def test_paths_to_major_minors_a_path_doesnt_exist(self):
        self.block_devices.node_block_devices = self.node_block_devices
        devices = self.block_devices.paths_to_major_minors(['/dev/disk/by-id/idontexist',
                                                            '/dev/disk/by-id/adisk'])
        self.assertEqual(devices, ['12:24'])
