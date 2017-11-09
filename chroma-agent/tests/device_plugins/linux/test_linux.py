import collections
import json
import errno
import os
import mock
from django.utils import unittest

from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices, NormalizedDeviceTable
from chroma_agent.device_plugins.linux_components.device_mapper import DmsetupTable


# included for legacy tests
class MockDmsetupTable(DmsetupTable):
    def __init__(self, dmsetup_data, devices_data):
        self.lvs = devices_data['lvs']
        self.vgs = devices_data['vgs']
        self.mpaths = {}
        with mock.patch('chroma_agent.utils.BlkId', return_value={}):
            with mock.patch(
                    'chroma_agent.device_plugins.linux_components.block_devices.parse_sys_block',
                    return_value=(devices_data['block_device_nodes'],
                                  devices_data['node_block_devices'],
                                  NormalizedDeviceTable([]),
                                  None,
                                  None)):
                self.block_devices = BlockDevices()
        self._parse_dm_table(dmsetup_data)


class LinuxAgentTests(unittest.TestCase):
    def setUp(self):
        super(LinuxAgentTests, self).setUp()

        tests = os.path.join(os.path.dirname(__file__), '../../')
        self.test_root = os.path.join(tests, "data/device_plugins/linux")
        mock.patch('chroma_agent.lib.shell.AgentShell.run').start()

        self.existing_files = []

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def assertNormalizedPaths(self, normalized_values, ndt):
        class mock_open:
            def __init__(self, fname):
                pass

            def read(self):
                return "root=/not/a/real/path"

        with mock.patch('__builtin__.open', mock_open):
            for path, expected_path in normalized_values.items():
                actual_path = ndt.normalized_device_path(path)
                self.assertEqual(expected_path, actual_path,
                                 "Normalized path failure %s != %s" %
                                 (expected_path, actual_path))


class DummyDataTests(LinuxAgentTests):
    def setUp(self):
        super(DummyDataTests, self).setUp()

        self.load_fixture(u'device_scanner.json')
        self.load_expected(u'agent_plugin.json')

    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def load_fixture(self, filename):
        str_data = self.load(filename)
        fixture = json.loads(str_data)

        with mock.patch('glob.glob', return_value=[]):
            with mock.patch(
                    'chroma_agent.device_plugins.linux_components.block_devices.scanner_cmd',
                    return_value=fixture):
                self.block_devices = BlockDevices()

    def load_expected(self, filename):
        str_data = self.load(filename)
        self.expected = json.loads(str_data)['result']['linux']


class TestBlockDevices(DummyDataTests):
    def test_block_device_lvm_output(self):
        [self.assertEqual(getattr(self.block_devices, x), self.expected[x]) for x in ['vgs', 'lvs']]

    def test_block_device_nodes_parsing(self):
        result = self.block_devices.block_device_nodes

        self.assertEqual(result['8:48'], self.expected['devs']['8:48'])

        # partition
        self.assertEqual(result['8:49'], self.expected['devs']['8:49'])

        # dm-0 linear lvm
        self.assertEqual(result['253:0'], self.expected['devs']['253:0'])

        # dm-2 striped lvm
        self.assertEqual(result['253:2'], self.expected['devs']['253:2'])

    def test_node_block_devices_parsing(self):
        result = self.block_devices.node_block_devices

        self.assertEqual(result[u'/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk3'], u'8:48')

        # partition
        self.assertEqual(result[u'/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk3-part1'], u'8:49')

        # dm-0 linear lvm
        self.assertEqual(result[u'/dev/mapper/vg_00-lv_root'], u'253:0')

        # dm-2 striped lvm
        self.assertEqual(result[u'/dev/mapper/vg_01-stripedlv'], u'253:2')

    def test_normalized_device_table(self):
        self.load_fixture(u'device_scanner_mpath.json')
        self.load_expected(u'agent_plugin_mpath.json')

        result = self.block_devices.normalized_device_table.table

        self.assertEqual(result[
                u'/dev/disk/by-id/scsi-35000c50068b5a1c7'],
            u"/dev/mapper/35000c50068b5a1c7")


class TestDevMajorMinor(DummyDataTests):
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
            'chroma_agent.device_plugins.linux_components.block_devices.parse_sys_block',
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


class TestZfsDevices(DummyDataTests):
    def setUp(self):
        super(DummyDataTests, self).setUp()

        self.load_fixture(u'device_scanner_zfs.json')
        self.load_expected(u'agent_plugin_zfs.json')

    def test_zfs_device_output(self):
        [self.assertEqual(getattr(self.block_devices, x), self.expected[x]) for x in ['zfspools', 'zfsdatasets']]

        for mm in ['zfspool:0xD322CC960F8137BC', 'zfsset:testPool3/backup', 'zfsset:testPool3/homer']:
            self.assertEqual(self.block_devices.block_device_nodes[mm], self.expected['devs'][mm])

    # todo: drive mm and size tests
