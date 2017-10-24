import collections
import json
import errno
import os
import mock
from django.utils import unittest

# from chroma_agent.device_plugins.linux import DmsetupTable
from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices
import chroma_agent.lib.normalize_device_path as ndp


# class MockDmsetupTable(DmsetupTable):
#     def __init__(self, dmsetup_data, devices_data):
#         self.lvs = devices_data['lvs']
#         self.vgs = devices_data['vgs']
#         self.mpaths = {}
#         with mock.patch('chroma_agent.utils.BlkId', return_value={}):
#             with mock.patch(
#                     'chroma_agent.device_plugins.linux_components.block_devices.BlockDevices._parse_sys_block',
#                     return_value=(devices_data['block_device_nodes'],
#                                   devices_data['node_block_devices'])):
#                 self.block_devices = BlockDevices()
#         self._parse_dm_table(dmsetup_data)


class LinuxAgentTests(unittest.TestCase):
    def setUp(self):
        super(LinuxAgentTests, self).setUp()

        tests = os.path.join(os.path.dirname(__file__), '../../')
        self.test_root = os.path.join(tests, "data/device_plugins/linux")

        self.load_fixture(u'/devices/pci0000:00/0000:00:05.0/virtio1/host2/target2:0:0/2:0:0:3/block/sdc')
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
        fixture = {device_key: dict_data[device_key]}

        with mock.patch('glob.glob', return_value=[]):
            with mock.patch(
                    'chroma_agent.device_plugins.linux_components.block_devices.scanner_cmd',
                    return_value=fixture):
                self.block_devices = BlockDevices()

    def load_expected(self, filename='agent_plugin.json'):
        str_data = self.load(filename)
        self.expected = json.loads(str_data)["result"]["linux"]


# {"/devices/pci0000:00/0000:00:0d.0/ata11/host10/target10:0:0/10:0:0:0/block/sdi":
#            {
#                "ACTION":
#                    "add",
#                "MAJOR":
#                    "8",
#                "MINOR":
#                    "128",
#                "DEVLINKS":
#                    "/dev/disk/by-id/ata-VBOX_HARDDISK_VB94952694-0a23e192 /dev/disk/by-label/fs-OST0006 /dev/disk/by-path/pci-0000:00:0d.0-ata-9.0 /dev/disk/by-uuid/f21688ec-5bde-44a5-9ace-c7c4b18a20f5",
#                "PATHS": [
#                    "/dev/sdi",
#                    "/dev/disk/by-id/ata-VBOX_HARDDISK_VB94952694-0a23e192",
#                    "/dev/disk/by-label/fs-OST0006",
#                    "/dev/disk/by-path/pci-0000:00:0d.0-ata-9.0",
#                    "/dev/disk/by-uuid/f21688ec-5bde-44a5-9ace-c7c4b18a20f5"
#                ],
#                "DEVNAME":
#                    "/dev/sdi",
#                "DEVPATH":
#                    "/devices/pci0000:00/0000:00:0d.0/ata11/host10/target10:0:0/10:0:0:0/block/sdi",
#                "DEVTYPE":
#                    "disk",
#                "ID_VENDOR":
#                    None,
#                "ID_MODEL":
#                    "VBOX_HARDDISK",
#                "ID_SERIAL":
#                    "VBOX_HARDDISK_VB94952694-0a23e192",
#                "ID_FS_TYPE":
#                    "ext4",
#                "ID_PART_ENTRY_NUMBER":
#                    None,
#                "IML_SIZE":
#                    "10485760",
#                "IML_SCSI_80":
#                    "SATA     VBOX HARDDISK   VB94952694-0a23e192",
#                "IML_SCSI_83":
#                    "1ATA     VBOX HARDDISK                           VB94952694-0a23e192",
#                "IML_IS_RO":
#                    False
#            }
#        }


# class TestDmSetupParse(DummyDataTestCase):
#     def _test_dmsetup(self, devices_filename, dmsetup_filename,
#                       mpaths_filename, normalized_paths_filename):
#         devices_data = json.loads(self.load(devices_filename))
#         dmsetup_data = self.load(dmsetup_filename)
#         actual_mpaths = MockDmsetupTable(dmsetup_data, devices_data).mpaths
#         expected_mpaths = json.loads(self.load(mpaths_filename))
#         expected_normalized_paths = json.loads(
#             self.load(normalized_paths_filename))
#
#         self.assertDictEqual(actual_mpaths, expected_mpaths)
#         self.assertNormalizedPaths(expected_normalized_paths)
#
#     def test_dmsetup_table(self):
#         """This is a regression test using data from a test/dev machine which includes LVs and multipath, all the data
#            is just as it is when run through on Chroma 1.0.0.0: this really is a *regression* test rather than
#            a correctness test.  The system from which this data was gathered ran CentOS 5.6"""
#         self._test_dmsetup('devices_1.json', 'dmsetup_1.json', 'mpaths_1.json',
#                            'normalized_1.json')
#
#     def test_HYD_1383(self):
#         """Minimal reproducer for HYD-1383.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
#            let it run through far enough to experience failure."""
#         self._test_dmsetup(
#             'devices_NTAP-12-min.json', 'dmsetup_NTAP-12-min.json',
#             'mpaths_NTAP-12-min.json', 'normalized_NTAP-12-min.json')
#
#     def test_HYD_1385(self):
#         """Minimal reproducer for HYD-1385.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
#            let it run through far enough to experience failure."""
#         self._test_dmsetup('devices_HYD-1385.json', 'dmsetup_HYD-1385.json',
#                            'mpaths_HYD-1385.json', 'normalized_HYD-1385.json')
#
#     def test_HYD_1390(self):
#         """Minimal reproducer for HYD-1385.  The `dmsetup table` output is authentic, the other inputs are hand crafted to
#            let it run through far enough to experience failure."""
#         self._test_dmsetup('devices_HYD-1390.json', 'dmsetup_HYD-1390.json',
#                            'mpaths_HYD-1390.json', 'normalized_HYD-1390.json')


class TestBlockDevices(LinuxAgentTests):
    def test_block_device_nodes_parsing(self):
        result = self.block_devices.block_device_nodes

        self.assertEqual(result, {"8:32": self.expected["devs"]["8:32"]})

    #        {
    #            "8:128": {
    #                "size":
    #                    5368709120,
    #                "device_path":
    #                    "/devices/pci0000:00/0000:00:0d.0/ata11/host10/target10:0:0/10:0:0:0/block/sdi",
    #                "major_minor":
    #                    "8:128",
    #                "partition_number":
    #                    None,
    #                "device_type":
    #                    "disk",
    #                "path":
    #                    "/dev/disk/by-id/ata-VBOX_HARDDISK_VB94952694-0a23e192",
    #                "filesystem_type":
    #                    "ext4",
    #                "paths": [
    #                    "/dev/disk/by-id/ata-VBOX_HARDDISK_VB94952694-0a23e192",
    #                    "/dev/disk/by-path/pci-0000:00:0d.0-ata-9.0", "/dev/sdi",
    #                    "/dev/disk/by-label/fs-OST0006",
    #                    "/dev/disk/by-uuid/f21688ec-5bde-44a5-9ace-c7c4b18a20f5"
    #                ],
    #                "parent":
    #                    None,
    #                "serial_83":
    #                    "1ATA     VBOX HARDDISK                           VB94952694-0a23e192",
    #                "serial_80":
    #                    "SATA     VBOX HARDDISK   VB94952694-0a23e192",
    #                "is_ro":
    #                    False,
    #                'dm_lv': None,
    #                'dm_multipath': None,
    #                'dm_slave_mms': [],
    #                'dm_uuid': None,
    #                'dm_vg': None,
    #                'dm_vg_size': None,
    #            }
    #        })

    def test_dm_block_device_nodes_parsing(self):
        # result = self.block_devices.block_device_nodes

        pass

    def test_node_block_devices_parsing(self):
        result = self.block_devices.node_block_devices

        self.assertEqual(result,
                         {u'/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk4': u'8:32'})


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
