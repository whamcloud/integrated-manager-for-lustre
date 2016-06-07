import collections
import errno
import mock

from chroma_agent.device_plugins.linux_components.device_helper import DeviceHelper
from tests.device_plugins.linux.test_linux import LinuxAgentTests


class TestDeviceHelper(LinuxAgentTests):

    MockDevice = collections.namedtuple('MockDevice', 'st_mode st_rdev')

    mock_devices = {
        '/dev/disk/by-id/adisk': MockDevice(25008, 6)
    }

    def mock_os_stat(self, path):
        if path in TestDeviceHelper.mock_devices:
            return TestDeviceHelper.mock_devices[path]
        else:
            raise OSError(errno.ENOENT, 'No such file or directory.')

    def mock_os_major(self, st_rdev):
        return st_rdev * 2

    def mock_os_minor(self, st_rdev):
            return st_rdev * 4

    def setUp(self):
        super(TestDeviceHelper, self).setUp()
        mock.patch('os.stat', self.mock_os_stat).start()
        mock.patch('os.major', self.mock_os_major).start()
        mock.patch('os.minor', self.mock_os_minor).start()
        self.addCleanup(mock.patch.stopall)
        self.device_helper = DeviceHelper()

    def test_dev_major_minor_path_exists(self):
        path = '/dev/disk/by-id/adisk'
        device = self.device_helper._dev_major_minor(path)
        self.assertEqual(device, '12:24')

    def test_dev_major_minor_path_doesnt_exist(self):
        path = '/dev/disk/by-id/idontexist'
        device = self.device_helper._dev_major_minor(path)
        self.assertEqual(device, None)

    def test_paths_to_major_minors_paths_exist(self):
        devices = self.device_helper._paths_to_major_minors(['/dev/disk/by-id/adisk'])
        self.assertEqual(len(devices), 1)

    def test_paths_to_major_minors_a_path_doesnt_exist(self):
        devices = self.device_helper._paths_to_major_minors(['/dev/disk/by-id/adisk', '/dev/disk/by-id/idontexist'])
        self.assertEqual(devices, [])
