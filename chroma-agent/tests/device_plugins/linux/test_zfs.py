from mock import patch

from chroma_agent.device_plugins.linux import ZfsDevices
from chroma_agent.device_plugins.linux import BlockDevices
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

    class mock_open(object):
        def __init__(self, fname):
            pass

        def read(self):
            return ""

    @patch('glob.glob', mock_empty_list)
    @patch('logging.Logger.debug', mock_debug)
    @patch('chroma_agent.utils.BlkId', dict)
    @patch('__builtin__.open', mock_open)
    @patch('chroma_agent.device_plugins.linux.DeviceHelper._find_block_devs', mock_empty_dict)
    def _setup_zfs_devices(self):
        blockdevices = BlockDevices()

        zfs_devices = ZfsDevices()
        zfs_devices.full_scan(blockdevices)

        return zfs_devices

    def test_imported_zfs(self):
        self.add_commands(CommandCaptureCommand(('partprobe', )),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health"), stdout="""
    zfsPool1        1T    1234567890ABCDE    ONLINE
    zfsPool2        1G    111111111111111    OFFLINE\n"""),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"), stdout="""
    zfsPool1        1T    1234567890ABCDE
    zfsPool1/mgt    1T    ABCDEF123456789
    zfsPool1/mgs    1T    AAAAAAAAAAAAAAA
    zfsPool2        1G    111111111111111
    zfsPool2/mgt    1G    222222222222222\n"""),
                          CommandCaptureCommand(("zpool", "status", "zfsPool1"), stdout=""" pool: zpool1
 state: ONLINE
  scan: none requested
config:

	NAME                               STATE     READ WRITE CKSUM
	zfsPool1  ONLINE       0     0     0
	  scsi-SCSI_DISK_1  ONLINE       0     0     0

errors: No known data errors)"""),
                          CommandCaptureCommand(("zpool", "import"), rc=1))

        zfs_devices = self._setup_zfs_devices()

        self.assertEqual(zfs_devices.zpools, {})
        self.assertEqual(zfs_devices.datasets, self.zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, self.zfs_results['zvols'])

    def test_exported_zfs_datasets_zvols(self):
        self.add_commands(
            CommandCaptureCommand(("partprobe", )),
            CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health")),
            CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health", "zfsPool1"),
                                  stdout="""
    zfsPool1        1T    1234567890ABCDE    ONLINE\n"""),
            CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"), stdout="""
    zfsPool1        1T    1234567890ABCDE
    zfsPool1/mgt    1T    ABCDEF123456789
    zfsPool1/mgs    1T    AAAAAAAAAAAAAAA\n"""),
            CommandCaptureCommand(("zpool", "status", "zfsPool1"), stdout=""" pool: zpool1
 state: ONLINE
  scan: none requested
config:

	NAME                               STATE     READ WRITE CKSUM
	zfsPool1  ONLINE       0     0     0
	  scsi-SCSI_DISK_1  ONLINE       0     0     0

errors: No known data errors)"""),
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
            CommandCaptureCommand(("zpool", "import", "-f", "-o", "readonly=on", "zfsPool1")),
            CommandCaptureCommand(("zpool", "export", "zfsPool1")),
            CommandCaptureCommand(("zpool", "import", "-f", "-o", "readonly=on", "zfsPool3"), rc=1, stderr="cannot import 'zfsPool3': no such pool available"))

        zfs_devices = self._setup_zfs_devices()

        self.assertEqual(zfs_devices.zpools, {})
        self.assertEqual(zfs_devices.datasets, self.zfs_results['datasets'])
        self.assertEqual(zfs_devices.zvols, self.zfs_results['zvols'])

    def test_exported_zfs_no_datasets_zvols(self):
        self.add_commands(
            CommandCaptureCommand(("partprobe", )),
            CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health")),
            CommandCaptureCommand(("zpool", "list", "-H", "-o", "name,size,guid,health", "zfsPool1"),
                                  stdout="""
    zfsPool1        1T    1234567890ABCDE    ONLINE\n"""),
            CommandCaptureCommand(("zfs", "list", "-H", "-o", "name,avail,guid"), stdout=""),
            CommandCaptureCommand(("zpool", "status", "zfsPool1"), stdout=""" pool: zpool1
 state: ONLINE
  scan: none requested
config:

	NAME                               STATE     READ WRITE CKSUM
	zfsPool1  ONLINE       0     0     0
	  scsi-SCSI_DISK_1  ONLINE       0     0     0

errors: No known data errors)"""),
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
            CommandCaptureCommand(("zpool", "import", "-f", "-o", "readonly=on", "zfsPool1")),
            CommandCaptureCommand(("zpool", "export", "zfsPool1")),
            CommandCaptureCommand(("zpool", "import", "-f", "-o", "readonly=on", "zfsPool3"), rc=1, stderr="cannot import 'zfsPool3': no such pool available"))

        zfs_devices = self._setup_zfs_devices()

        self.assertEqual(zfs_devices.zpools, self.zfs_results['zpools'])
        self.assertEqual(zfs_devices.datasets, {})
        self.assertEqual(zfs_devices.zvols, {})
