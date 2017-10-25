import collections
import json
import errno
import os
import mock
from django.utils import unittest

import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices


class LinuxAgentTests(unittest.TestCase):
    def setUp(self):
        super(LinuxAgentTests, self).setUp()

        tests = os.path.join(os.path.dirname(__file__), '../../')
        self.test_root = os.path.join(tests, "data/device_plugins/linux")

        self.load_fixture(u'/devices/pci0000:00/0000:00:05.0/virtio1/host0/target0:0:0/0:0:0:2/block/sdd')
        self.load_expected()

        self.existing_files = []

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def assertNormalizedPaths(self, normalized_values):
        class mock_open:
            def __init__(self, fname):
                pass

            def read(self):
                return "root=/not/a/real/path"

        with mock.patch('__builtin__.open', mock_open):
            for path, normalized_path in normalized_values.items():
                self.assertEqual(normalized_path,
                                 ndp.normalized_device_path(path),
                                 "Normalized path failure %s != %s" %
                                 (normalized_path,
                                  ndp.normalized_device_path(path)))

    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def load_fixture(self, device_key, filename='device_scanner.json'):
        str_data = self.load(filename)
        dict_data = json.loads(str_data)
        if device_key is None:
            fixture = dict_data
        else:
            fixture = {device_key: dict_data[device_key]}

        with mock.patch('glob.glob', return_value=[]):
            with mock.patch(
                    'chroma_agent.device_plugins.linux_components.block_devices.scanner_cmd',
                    return_value=fixture):
                self.block_devices = BlockDevices()

    def load_expected(self, filename='agent_plugin.json'):
        str_data = self.load(filename)
        self.expected = json.loads(str_data)['result']['linux']


class TestBlockDevices(LinuxAgentTests):
    def test_block_device_nodes_parsing(self):
        result = self.block_devices.block_device_nodes

        self.assertEqual(result, {'8:48': self.expected['devs']['8:48']})

    def test_node_block_devices_parsing(self):
        result = self.block_devices.node_block_devices

        self.assertEqual(result,
                         {u'/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk3': u'8:48'})

    def test_partition_block_device_nodes_parsing(self):
        # load entire device_scanner output so parent of partition can be resolved
        self.load_fixture(None)
        result = self.block_devices.block_device_nodes

        self.assertEqual(result['8:49'], self.expected['devs']['8:49'])

    def test_partition_node_block_devices_parsing(self):
        self.load_fixture(u'/devices/pci0000:00/0000:00:05.0/virtio1/host0/target0:0:0/0:0:0:2/block/sdd/sdd1')
        result = self.block_devices.node_block_devices

        self.assertEqual(result,
                         {u'/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk3-part1': u'8:49'})

    def test_dm_block_device_nodes_parsing(self):
        self.load_fixture(u'/devices/virtual/block/dm-0')
        result = self.block_devices.block_device_nodes

        self.assertEqual(result, {'253:0': self.expected['devs']['253:0']})

    def test_dm_node_block_devices_parsing(self):
        self.load_fixture(u'/devices/virtual/block/dm-0')
        result = self.block_devices.node_block_devices

        self.assertEqual(result,
                         {u'/dev/mapper/vg_00-lv_root': u'253:0'})

#    def test_dm_striped_block_device_nodes_parsing(self):
#        self.load_fixture(u'/devices/virtual/block/dm-0')
#        result = self.block_devices.block_device_nodes
#
#        self.assertEqual(result, {"253:0": self.expected["devs"]["253:0"]})
#
#    def test_dm_striped_node_block_devices_parsing(self):
#        self.load_fixture(u'/devices/virtual/block/dm-0')
#        result = self.block_devices.node_block_devices
#
#        self.assertEqual(result,
#                         {u'/dev/mapper/vg_00-lv_root': u'253:0'})
#
#    def test_dm_mpath_block_device_nodes_parsing(self):
#        self.load_fixture(u'/devices/virtual/block/dm-0')
#        result = self.block_devices.block_device_nodes
#
#        self.assertEqual(result, {"253:0": self.expected["devs"]["253:0"]})
#
#    def test_dm_mpath_node_block_devices_parsing(self):
#        self.load_fixture(u'/devices/virtual/block/dm-0')
#        result = self.block_devices.node_block_devices
#
#        self.assertEqual(result,
#                         {u'/dev/mapper/vg_00-lv_root': u'253:0'})


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
        mock.patch(
            'chroma_agent.utils.BlkId',
            return_value={
                0: {
                    'path': self.mock_devices.keys()[0],
                    'type': 'ext4'
                }
            }).start()
        mock.patch(
            'chroma_agent.device_plugins.linux_components.block_devices.BlockDevices._parse_sys_block',
            return_value=(None, None, None)).start()
        self.addCleanup(mock.patch.stopall)

    def test_paths_to_major_minors_paths_exist(self):
        self.block_devices.node_block_devices = self.node_block_devices
        devices = self.block_devices.paths_to_major_minors(
            ['/dev/disk/by-id/adisk'])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices, ['12:24'])

    def test_paths_to_major_minors_a_path_doesnt_exist(self):
        self.block_devices.node_block_devices = self.node_block_devices
        devices = self.block_devices.paths_to_major_minors(
            ['/dev/disk/by-id/idontexist', '/dev/disk/by-id/adisk'])
        self.assertEqual(devices, ['12:24'])
