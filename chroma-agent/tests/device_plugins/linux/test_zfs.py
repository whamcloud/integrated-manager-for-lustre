from mock import patch, Mock, MagicMock, call, PropertyMock

from chroma_agent.device_plugins.linux import ZfsDevices
from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices
from chroma_agent.device_plugins.linux_components.zfs import get_zpools, _get_all_zpool_devices
from tests.data import zfs_example_data
from tests.device_plugins.linux.test_linux import LinuxAgentTests
from iml_common.test.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand

zfs_results = {'datasets': {'ABCDEF123456789': {'uuid': 'ABCDEF123456789',
                                                'name': 'zfsPool3/mgt',
                                                'block_device': 'zfsset:ABCDEF123456789',
                                                'drives': [],
                                                'path': 'zfsPool3/mgt',
                                                'size': 1099511627776},
                            'AAAAAAAAAAAAAAA': {'uuid': 'AAAAAAAAAAAAAAA',
                                                'name': 'zfsPool3/mgs',
                                                'block_device': 'zfsset:AAAAAAAAAAAAAAA',
                                                'drives': [],
                                                'path': 'zfsPool3/mgs',
                                                'size': 1099511627776}},
               'zpools': {'2234567890ABCDE': {'block_device': 'zfspool:zfsPool1',
                                              'drives': [],
                                              'name': 'zfsPool1',
                                              'path': 'zfsPool1',
                                              'size': 1099511627776,
                                              'uuid': '2234567890ABCDE'}},
               'zvols': {}}

zpool_zfsPool3_result = {'block_device': 'zfspool:zfsPool3',
                         'drives': [],
                         'name': 'zfsPool3',
                         'path': 'zfsPool3',
                         'size': 1099511627776,
                         'uuid': '222222222222222'}

dev_results = {'zfspool:zfsPool1': {'filesystem_type': None,
                                    'major_minor': 'zfspool:zfsPool1',
                                    'parent': None,
                                    'path': 'zfsPool1',
                                    'paths': ['zfsPool1'],
                                    'serial_80': None,
                                    'serial_83': None,
                                    'size': 1099511627776},
               'zfsset:AAAAAAAAAAAAAAA': {'filesystem_type': 'zfs',
                                          'major_minor': 'zfsset:AAAAAAAAAAAAAAA',
                                          'parent': None,
                                          'path': 'zfsPool3/mgs',
                                          'paths': ['zfsPool3/mgs'],
                                          'serial_80': None,
                                          'serial_83': None,
                                          'size': 1099511627776},
               'zfsset:ABCDEF123456789': {'filesystem_type': 'zfs',
                                          'major_minor': 'zfsset:ABCDEF123456789',
                                          'parent': None,
                                          'path': 'zfsPool3/mgt',
                                          'paths': ['zfsPool3/mgt'],
                                          'serial_80': None,
                                          'serial_83': None,
                                          'size': 1099511627776}}


def read_from_store_side_effect(id):
    # store will return pools and datasets and zvois for a given pool id
    return {zpool_zfsPool3_result['uuid']: {'pool': zpool_zfsPool3_result,
                                            'datasets': zfs_results['datasets'],
                                            'zvols': zfs_results['zvols']}}[id]


class TestZfs(LinuxAgentTests, CommandCaptureTestCase):

    def setUp(self):
        super(TestZfs, self).setUp()

    def mock_debug(self, value):
        print value

    def mock_empty_list(*arg):
        return []

    def mock_empty_dict(*arg):
        return {}

    def mock_find_device_and_children(path, ndt):
        return [path]

    mock_read_from_store = MagicMock(side_effect=read_from_store_side_effect)

    mock_write_to_store = MagicMock()

    mock_device_nodes = MagicMock(spec_set=dict)

    @patch('glob.glob', mock_empty_list)
    @patch('logging.Logger.debug', Mock())  # mock_debug)
    @patch('chroma_agent.utils.BlkId', dict)
    @patch('chroma_agent.device_plugins.linux_components.block_devices.scanner_cmd', mock_empty_dict)
    @patch('chroma_agent.device_plugins.linux_components.zfs.ZfsDevice')
    @patch('chroma_agent.device_plugins.linux_components.zfs.read_from_store', mock_read_from_store)
    @patch('chroma_agent.device_plugins.linux_components.zfs.write_to_store', mock_write_to_store)
    def _setup_zfs_devices(self, mock_zfs_device, available_side_effect=None):
        # mock context manager __enter__ returned object
        type(mock_zfs_device.return_value.__enter__.return_value).available = PropertyMock(
            return_value=True) if available_side_effect is None else PropertyMock(side_effect=available_side_effect)

        self.mock_read_from_store.reset_mock()
        self.mock_write_to_store.reset_mock()

        block_devices = BlockDevices()

        zfs_devices = ZfsDevices()
        zfs_devices.full_scan(block_devices)

        return zfs_devices, block_devices

    @patch('chroma_agent.device_plugins.linux_components.zfs.find_device_and_children', mock_find_device_and_children)
    def _get_zfs_devices(self, pool_name):
        """ test the process of using full partition paths and device basenames to resolve device paths """
        return _get_all_zpool_devices(pool_name, None)

    def test_get_active_zpool(self):
        """ WHEN active/imported zpools are output from 'zpool status' command THEN parser returns relevant pools """
        self.add_commands(CommandCaptureCommand(("zpool", "status"),
                                                stdout=zfs_example_data.multiple_imported_pools_status))

        zpools = get_zpools()

        self.assertRanAllCommandsInOrder()
        self.assertListEqual(['zfsPool3', 'zfsPool1'], [pool['pool'] for pool in zpools])
        [self.assertListEqual(['errors', 'scan', 'devices', 'state', 'pool'], pool.keys()) for pool in zpools]

    def test_get_no_active_zpools(self):
        """ WHEN no active/imported zpools are output from 'zpool status' command THEN parser returns empty list """
        self.add_commands(CommandCaptureCommand(("zpool", "status"),
                                                stdout="no pools available\n"))

        zpools = get_zpools()

        self.assertRanAllCommandsInOrder()
        self.assertListEqual([], zpools)

    def test_get_inactive_zpool(self):
        """ WHEN inactive/exported zpools are output from 'zpool import' command THEN parser returns relevant pools """
        self.add_commands(CommandCaptureCommand(("zpool", "import"),
                                                stdout=zfs_example_data.multiple_exported_online_pools))

        zpools = get_zpools(active=False)

        self.assertRanAllCommandsInOrder()
        self.assertListEqual(['zfsPool1', 'zfsPool2', 'zfsPool3'], [pool['pool'] for pool in zpools])
        [self.assertListEqual(['devices', 'state', 'action', 'id', 'pool'], pool.keys()) for pool in zpools]

    def test_already_imported_zpool(self):
        """
        WHEN zpool is already imported which has datasets,
        AND there are no other pools to import,
        THEN only the datasets (not zpool) are reported.
        """
        self.add_commands(CommandCaptureCommand(("udevadm", "settle")),
                          CommandCaptureCommand(("zpool", "status"),
                                                stdout=zfs_example_data.multiple_imported_pools_status),
                          CommandCaptureCommand(("zpool", "import"),
                                                stdout="no pools available to import\n"),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid", 'zfsPool3'),
                                                stdout="zfsPool3        1T    1234567890ABCDE\n"),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", 'zfsPool3'),
                                                stdout="zfsPool3        1T    1234567890ABCDE    ONLINE\n"),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", 'zfsPool3'),
                                                stdout="zfsPool3        1T    1234567890ABCDE    ONLINE\n"),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"),
                                                stdout="""zfsPool3        1T    1234567890ABCDE
zfsPool3/mgt    1T    ABCDEF123456789
zfsPool3/mgs    1T    AAAAAAAAAAAAAAA\n"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid", 'zfsPool1'),
                                                stdout="zfsPool1        1T    2234567890ABCDE\n"),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", 'zfsPool1'),
                                                stdout="zfsPool1        1T    2234567890ABCDE    ONLINE\n"),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", 'zfsPool1'),
                                                stdout="zfsPool1        1T    2234567890ABCDE    ONLINE\n"),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"),
                                                stdout="""zfsPool1        1T    2234567890ABCDE\n"""))

        zfs_devices, block_devices = self._setup_zfs_devices()

        self.assertRanAllCommandsInOrder()
        self.assertEqual(zfs_devices.zpools, zfs_results['zpools'])
        self.assertEqual(zfs_devices.datasets, zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, zfs_results['zvols'])

        self.maxDiff = 5000
        # verify blockdevices device_nodes also have been updated
        self.assertDictEqual(block_devices.block_device_nodes, dev_results)

    def test_exported_zpools(self):
        """
        WHEN one inactive zpool is imported which has datasets,
        AND one inactive zpool is offline,
        AND one inactive zpool is imported but doesn't have datasets,
        THEN the datasets (not zpool) are reported,
        AND the offline zpool is not reported,
        AND the zpool without datasets is reported.
        """
        self.add_commands(CommandCaptureCommand(("udevadm", "settle")),
                          CommandCaptureCommand(("zpool", "status"),
                                                stderr='no pools available\n'),
                          CommandCaptureCommand(("zpool", "import"),
                                                stdout=zfs_example_data.multiple_exported_online_offline_pools),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid", 'zfsPool1'),
                                                stdout="zfsPool1        1T    2234567890ABCDE\n"),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool1"),
                                                stdout="""zfsPool1
        /dev/disk/by-id/scsi-SCSI_DISK_3-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool1"),
                                                stdout="""zfsPool1
        scsi-SCSI_DISK_3   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"),
                                                stdout="""zfsPool1        1T    2234567890ABCDE
    zfsPool3        1T    1234567890ABCDE
    zfsPool3/mgt    1T    ABCDEF123456789
    zfsPool3/mgs    1T    AAAAAAAAAAAAAAA\n"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid", 'zfsPool3'),
                                                stdout="zfsPool3        1T    1234567890ABCDE\n"),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool3"),
                                                stdout="""zfsPool3
        /dev/disk/by-id/scsi-SCSI_DISK_1-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool3"),
                                                stdout="""zfsPool3
        scsi-SCSI_DISK_1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"),
                                                stdout="""zfsPool1        1T    2234567890ABCDE
    zfsPool3        1T    1234567890ABCDE
    zfsPool3/mgt    1T    ABCDEF123456789
    zfsPool3/mgs    1T    AAAAAAAAAAAAAAA\n"""))

        zfs_devices, block_devices = self._setup_zfs_devices(available_side_effect=[True, False, True])

        self.assertRanAllCommandsInOrder()
        self.assertEqual(zfs_devices.zpools, zfs_results['zpools'])
        self.assertEqual(zfs_devices.datasets, zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, zfs_results['zvols'])

        self.assertDictEqual(block_devices.block_device_nodes, dev_results)

    def test_exported_unavailable_zpool_fail(self):
        """
        WHEN inactive zpool is unavailable,
        AND try to read zpool info from store fails,
        THEN no zpool is reported.
        """
        self.add_commands(CommandCaptureCommand(("udevadm", "settle")),
                          CommandCaptureCommand(("zpool", "status"),
                                                stderr='no pools available\n'),
                          CommandCaptureCommand(("zpool", "import"),
                                                stdout=zfs_example_data.single_raidz2_unavail_pool))

        zfs_devices, block_devices = self._setup_zfs_devices(available_side_effect=[False])

        self.assertRanAllCommandsInOrder()
        self.mock_read_from_store.assert_called_once_with('14729155358256179095')
        self.assertEqual(zfs_devices.zpools, {})
        self.assertEqual(zfs_devices.datasets, {})
        self.assertEqual(zfs_devices.zvols, {})

        self.assertDictEqual(block_devices.block_device_nodes, {})

    def test_exported_unavailable_zpool_success(self):
        """
        WHEN inactive zpool is unavailable,
        AND try to read zpool info from store succeeds,
        THEN expected  are reported.
        """
        self.add_commands(CommandCaptureCommand(("udevadm", "settle")),
                          CommandCaptureCommand(("zpool", "status"),
                                                stderr='no pools available\n'),
                          CommandCaptureCommand(("zpool", "import"),
                                                stdout=zfs_example_data.single_raidz2_unavail_pool_B))

        zfs_devices, block_devices = self._setup_zfs_devices(available_side_effect=[False])

        self.assertRanAllCommandsInOrder()
        self.mock_read_from_store.assert_called_once_with('222222222222222')
        self.assertEqual(zfs_devices.zpools, {})
        self.assertEqual(zfs_devices.datasets, zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, zfs_results['zvols'])

        self.assertDictEqual(block_devices.block_device_nodes,
                             {k: dev_results[k] for k in dev_results.keys() if k.startswith('zfsset')})

    def test_saving_to_store(self):
        """
        WHEN inactive ONLINE zpool is imported,
        THEN correct zpool info is supplied in call to write to store.
        """
        self.add_commands(CommandCaptureCommand(("udevadm", "settle")),
                          CommandCaptureCommand(("zpool", "status"),
                                                stderr='no pools available\n'),
                          CommandCaptureCommand(("zpool", "import"),
                                                stdout=zfs_example_data.multiple_exported_online_offline_pools),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid", 'zfsPool1'),
                                                stdout="zfsPool1        1T    2234567890ABCDE\n"),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool1"),
                                                stdout="""zfsPool1
        /dev/disk/by-id/scsi-SCSI_DISK_3-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool1"),
                                                stdout="""zfsPool1
        scsi-SCSI_DISK_3   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"),
                                                stdout="""zfsPool1        1T    2234567890ABCDE
    zfsPool3        1T    222222222222222
    zfsPool3/mgt    1T    ABCDEF123456789
    zfsPool3/mgs    1T    AAAAAAAAAAAAAAA\n"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid", 'zfsPool3'),
                                                stdout="zfsPool3        1T    222222222222222\n"),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool3"),
                                                stdout="""zfsPool3
        /dev/disk/by-id/scsi-SCSI_DISK_1-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool3"),
                                                stdout="""zfsPool3
        scsi-SCSI_DISK_1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"),
                                                stdout="""zfsPool1        1T    2234567890ABCDE
    zfsPool3        1T    222222222222222
    zfsPool3/mgt    1T    ABCDEF123456789
    zfsPool3/mgs    1T    AAAAAAAAAAAAAAA\n"""))

        zfs_devices, block_devices = self._setup_zfs_devices(available_side_effect=[True, False, True])

        self.assertRanAllCommandsInOrder()

        # store should have been populated with data from two ONLINE zpools, one with datasets and one without
        self.mock_write_to_store.assert_has_calls([call('2234567890ABCDE',
                                                        {'pool': zfs_results['zpools'].values()[0],
                                                         'datasets': {},
                                                         'zvols': {}}),
                                                   call('222222222222222',
                                                        {'pool': {'block_device': 'zfspool:zfsPool3',
                                                                  'drives': [],
                                                                  'name': 'zfsPool3',
                                                                  'path': 'zfsPool3',
                                                                  'size': 1099511627776,
                                                                  'uuid': '222222222222222'},
                                                         'datasets': zfs_results['datasets'],
                                                         'zvols': zfs_results['zvols']})])

        self.assertEqual(zfs_devices.zpools, zfs_results['zpools'])
        self.assertEqual(zfs_devices.datasets, zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, zfs_results['zvols'])

    def test_resolve_devices(self):
        """ Check when zpool contains multiple disks the listed partitions are resolved to the correct devices """
        self.add_commands(CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        /dev/sde1   9.94G   228K    9.94G   -       0%      0%
        /dev/disk/by-id/scsi-SCSI_DISK_1-part1   9.94G   228K    9.94G   -       0%      0%
        /dev/disk/by-id/scsi-SCSI_DISK_2-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        sde   9.94G   228K    9.94G   -       0%      0%
        scsi-SCSI_DISK_1   9.94G   228K    9.94G   -       0%      0%
        scsi-SCSI_DISK_2   9.94G   228K    9.94G   -       0%      0%\n"""))

        self.assertItemsEqual(self._get_zfs_devices('zfsPool1'),
                              ['/dev/disk/by-id/scsi-SCSI_DISK_1', '/dev/disk/by-id/scsi-SCSI_DISK_2', '/dev/sde'])
        self.assertRanAllCommandsInOrder()

    def test_resolve_devices_duplicate_device_basenames(self):
        """
        Check when zpool contains duplicate device basenames the listed partitions are resolved to the correct devices
        """
        self.add_commands(CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        /dev/sde1   9.94G   228K    9.94G   -       0%      0%
        /dev/disk/by-id/scsi-SCSI_DISK_1a/scsi-SCSI_DISK_1-part1   9.94G   228K    9.94G   -       0%      0%
        /dev/disk/by-id/scsi-SCSI_DISK_1b/scsi-SCSI_DISK_1-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        sde   9.94G   228K    9.94G   -       0%      0%
        scsi-SCSI_DISK_1   9.94G   228K    9.94G   -       0%      0%
        scsi-SCSI_DISK_1   9.94G   228K    9.94G   -       0%      0%\n"""))

        self.assertItemsEqual(self._get_zfs_devices('zfsPool1'), ['/dev/disk/by-id/scsi-SCSI_DISK_1a/scsi-SCSI_DISK_1',
                                                                  '/dev/disk/by-id/scsi-SCSI_DISK_1b/scsi-SCSI_DISK_1',
                                                                  '/dev/sde'])
        self.assertRanAllCommandsInOrder()

    def test_resolve_devices_multiple_matches(self):
        """
        Check when zpool contains device basenames which are a substring of another, the listed partitions are
        resolved to the correct devices
        """
        self.add_commands(CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        /dev/a/dev1111   9.94G   228K    9.94G   -       0%      0%
        /dev/b/dev111   9.94G   228K    9.94G   -       0%      0%
        /dev/c/dev11   9.94G   228K    9.94G   -       0%      0%
        /dev/d/dev1   9.94G   228K    9.94G   -       0%      0%
        /dev/disk/by-id2/md0-0011   9.94G   228K    9.94G   -       0%      0%
        /dev/disk/by-id1/md0-00111   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        dev   9.94G   228K    9.94G   -       0%      0%
        dev1   9.94G   228K    9.94G   -       0%      0%
        dev11   9.94G   228K    9.94G   -       0%      0%
        dev111   9.94G   228K    9.94G   -       0%      0%
        md0-0011   9.94G   228K    9.94G   -       0%      0%
        md0-001   9.94G   228K    9.94G   -       0%      0%\n"""))

        self.assertItemsEqual(self._get_zfs_devices('zfsPool1'), ['/dev/disk/by-id1/md0-0011',
                                                                  '/dev/disk/by-id2/md0-001',
                                                                  '/dev/d/dev',
                                                                  '/dev/c/dev1',
                                                                  '/dev/b/dev11',
                                                                  '/dev/a/dev111'])
        self.assertRanAllCommandsInOrder()
