from mock import patch, Mock

from chroma_agent.device_plugins.linux import ZfsDevices
from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices
from tests.device_plugins.linux.test_linux import LinuxAgentTests
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand


class TestZfs(LinuxAgentTests, CommandCaptureTestCase):

    def setUp(self):
        super(TestZfs, self).setUp()

        self.zfs_results = {'datasets': {'ABCDEF123456789': {'uuid': 'ABCDEF123456789',
                                                             'name': 'zfsPool1/mgt',
                                                             'block_device': 'zfsset:1',
                                                             'drives': [],
                                                             'path': 'zfsPool1/mgt',
                                                             'size': 1099511627776},
                                         'AAAAAAAAAAAAAAA': {'uuid': 'AAAAAAAAAAAAAAA',
                                                             'name': 'zfsPool1/mgs',
                                                             'block_device': 'zfsset:1',
                                                             'drives': [],
                                                             'path': 'zfsPool1/mgs',
                                                             'size': 1099511627776}},
                            'zpools': {'1234567890ABCDE': {'name': 'zfsPool1',
                                                           'block_device': 'zfspool:zfsPool1',
                                                           'path': 'zfsPool1', 'size': 1099511627776,
                                                           'drives': [], 'uuid': '1234567890ABCDE'}},
                            'zvols': {}}

    def mock_debug(self, value):
        print value

    def mock_empty_list(*arg):
        return []

    def mock_empty_dict(*arg):
        return {}

    def mock_find_device_and_children(self, path):
        return [path]

    @patch('glob.glob', mock_empty_list)
    @patch('logging.Logger.debug', mock_debug)
    @patch('chroma_agent.utils.BlkId', dict)
    @patch('chroma_agent.device_plugins.linux_components.block_devices.BlockDevices.find_block_devs', mock_empty_dict)
    @patch('chroma_agent.device_plugins.linux_components.zfs.ZfsDevice.lock_pool', Mock())
    @patch('chroma_agent.device_plugins.linux_components.zfs.ZfsDevice.unlock_pool', Mock())
    def _setup_zfs_devices(self):
        blockdevices = BlockDevices()

        zfs_devices = ZfsDevices()
        zfs_devices.full_scan(blockdevices)

        return zfs_devices

    @patch('chroma_agent.device_plugins.linux.ZfsDevices.find_device_and_children', mock_find_device_and_children)
    def _get_zfs_devices(self, pool_name):
        """ test the process of using full partition paths and device basenames to resolve device paths """
        return ZfsDevices()._get_all_zpool_devices(pool_name)

    def test_already_imported_zfs(self):
        """
        Check when zpool is already imported which has datasets, and no more pools to import,
        only the datasets (not zpool) are reported
        """
        self.add_commands(CommandCaptureCommand(("zpool", "list", "-H", "-o", "name"), stdout="""zfsPool1
zfsPool2\n"""),
                          CommandCaptureCommand(("zpool", "import"), rc=1),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name"), stdout="""zfsPool1
zfsPool2\n"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health", 'zfsPool2'),
                                                stdout="""zfsPool2        1G    111111111111111    OFFLINE\n"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name"), stdout="""zfsPool1
zfsPool2\n"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health", 'zfsPool1'),
                                                stdout="""zfsPool1        1T    1234567890ABCDE    ONLINE\n"""),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", 'zfsPool1'),
                                                stdout="""zfsPool1        1T    1234567890ABCDE    ONLINE\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", 'zfsPool1'),
                                                stdout="""zfsPool1        1T    1234567890ABCDE    ONLINE\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"), stdout="""
zfsPool1        1T    1234567890ABCDE
zfsPool1/mgt    1T    ABCDEF123456789
zfsPool1/mgs    1T    AAAAAAAAAAAAAAA
zfsPool2        1G    111111111111111
zfsPool2/mgt    1G    222222222222222\n"""))

        zfs_devices = self._setup_zfs_devices()

        self.assertRanAllCommandsInOrder()
        self.assertEqual(zfs_devices.zpools, {})
        self.assertEqual(zfs_devices.datasets, self.zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, self.zfs_results['zvols'])

    def test_exported_zfs_datasets_zvols(self):
        """ Check when zpool is imported which has datasets, only the datasets (not zpool) are reported """
        self.add_commands(CommandCaptureCommand(("zpool", "list", "-H", "-o", "name")),
                          CommandCaptureCommand(("zpool", "import"), stdout="""pool: zfsPool1
     id: 1234567890ABCDE
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool1  ONLINE
      scsi-SCSI_DISK_1  ONLINE

      pool: zfsPool2
     id: 111111111111111
  state: OFFLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool2  ONLINE
      scsi-SCSI_DISK_2  ONLINE

      pool: zfsPool3
     id: 222222222222222
  state: ONLINE
 action: The pool will fail when it is imported. Because of the error below.
 config:

    zfsPool3  ONLINE
      scsi-SCSI_DISK_3  ONLINE"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name")),
                          CommandCaptureCommand(("zpool", "import", "-f", "-N", "-o", "readonly=on", "-o", "cachefile=none", "zfsPool3"),
                                                rc=1, stderr="cannot import 'zfsPool3': no such pool available"),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name")),
                          CommandCaptureCommand(("zpool", "import", "-f", "-N", "-o", "readonly=on", "-o", "cachefile=none", "zfsPool1")),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health", "zfsPool1"),
                                                stdout="""
    zfsPool1        1T    1234567890ABCDE    ONLINE\n"""),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        /dev/disk/by-id/scsi-SCSI_DISK_1-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        scsi-SCSI_DISK_1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"), stdout="""\
    zfsPool1        1T    1234567890ABCDE
    zfsPool1/mgt    1T    ABCDEF123456789
    zfsPool1/mgs    1T    AAAAAAAAAAAAAAA\n"""),
                          CommandCaptureCommand(("zpool", "export", "zfsPool1")))

        zfs_devices = self._setup_zfs_devices()

        self.assertRanAllCommandsInOrder()
        self.assertEqual(zfs_devices.zpools, {})
        self.assertEqual(zfs_devices.datasets, self.zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, self.zfs_results['zvols'])

    def test_exported_zfs_no_datasets_zvols(self):
        """ Check when zpool is imported which has no datasets or zvols, only the zpool is reported """
        self.add_commands(CommandCaptureCommand(("zpool", "list", "-H", "-o", "name")),
                          CommandCaptureCommand(("zpool", "import"), stdout="""pool: zfsPool1
     id: 1234567890ABCDE
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool1  ONLINE
      scsi-SCSI_DISK_1  ONLINE

      pool: zfsPool2
     id: 111111111111111
  state: OFFLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool2  ONLINE
      scsi-SCSI_DISK_2  ONLINE

      pool: zfsPool3
     id: 222222222222222
  state: ONLINE
 action: The pool will fail when it is imported. Because of the error below.
 config:

    zfsPool3  ONLINE
      scsi-SCSI_DISK_3  ONLINE"""),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name")),
                          CommandCaptureCommand(("zpool", "import", "-f", "-N", "-o", "readonly=on", "-o", "cachefile=none", "zfsPool3"),
                                                rc=1, stderr="cannot import 'zfsPool3': no such pool available"),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name")),
                          CommandCaptureCommand(("zpool", "import", "-f", "-N", "-o", "readonly=on", "-o", "cachefile=none", "zfsPool1")),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health", "zfsPool1"),
                                                stdout="""
    zfsPool1        1T    1234567890ABCDE    ONLINE\n"""),
                          CommandCaptureCommand(("zpool", "list", "-PHv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        /dev/disk/by-id/scsi-SCSI_DISK_1-part1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zpool", "list", "-Hv", "-o", "name", "zfsPool1"), stdout="""\
zfsPool1
        scsi-SCSI_DISK_1   9.94G   228K    9.94G   -       0%      0%\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"), stdout=""),
                          CommandCaptureCommand(("zpool", "export", "zfsPool1")))

        zfs_devices = self._setup_zfs_devices()

        self.assertRanAllCommandsInOrder()
        self.assertEqual(zfs_devices.zpools, self.zfs_results['zpools'])
        self.assertEqual(zfs_devices.datasets, {})
        self.assertEqual(zfs_devices.zvols, {})

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
