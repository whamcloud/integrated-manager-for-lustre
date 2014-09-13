import json
import mock
import os
from django.utils import unittest

from chroma_agent.device_plugins.linux import DmsetupTable
import chroma_agent.lib.normalize_device_path as ndp


class MockDmsetupTable(DmsetupTable):
    def __init__(self, dmsetup_data, devices_data):
        self.lvs = devices_data['lvs']
        self.vgs = devices_data['vgs']
        self.mpaths = {}
        self.block_devices = mock.Mock()
        self.block_devices.node_block_devices = devices_data['node_block_devices']
        self.block_devices.block_device_nodes = devices_data['block_device_nodes']
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
