#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
import json
import os
from django.utils import unittest


class TestDmSetupParse(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/device_plugins/linux")

    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def test_dmsetup_table(self):
        """This is a regression test using data from a test/dev machine which includes LVs and multipath, all the data
           is just as it is when run through on Chroma 1.0.0.0: this really is a *regression* test rather than
           a correctness test.  The system from which this data was gathered ran CentOS 5.6"""
        self._test_dmsetup('devices_1.txt', 'dmsetup_1.txt', 'mpaths_1.txt')

    def _test_dmsetup(self, devices_filename, dmsetup_filename, mpaths_filename):
        from chroma_agent.device_plugins.linux import _parse_dm_table
        data = json.loads(self.load(devices_filename))
        mpaths = {}
        _parse_dm_table(self.load(dmsetup_filename), data['node_block_devices'], data['block_device_nodes'], data['vgs'], data['lvs'], mpaths)
        expected_mpaths = json.loads(self.load(mpaths_filename))
        self.assertDictEqual(mpaths, expected_mpaths)

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
