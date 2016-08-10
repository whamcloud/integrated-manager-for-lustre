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

    def setUp(self):
        super(TestDeviceHelper, self).setUp()
        self.stat_patcher = mock.patch('os.stat', self.mock_os_stat)
        self.stat_patcher.start()
        mock.patch('os.minor', lambda st_rdev: st_rdev * 4).start()
        mock.patch('os.major', lambda st_rdev: st_rdev * 2).start()
        mock.patch('stat.S_ISBLK', return_value=True).start()
        self.addCleanup(mock.patch.stopall)
        self.device_helper = DeviceHelper()
        self.device_helper.non_existent_paths = set([])

    def test_dev_major_minor_path_exists(self):
        """ After a successful attempt, path should be removed from no-retry list """
        path = '/dev/disk/by-id/adisk'
        self.device_helper.non_existent_paths.add(path)
        device = self.device_helper._dev_major_minor(path)
        self.assertNotIn(path, self.device_helper.non_existent_paths)
        self.assertEqual(device, '12:24')

    def test_dev_major_minor_path_doesnt_exist(self):
        """ After un-successful attempts, path should be added to no-retry list """
        path = '/dev/disk/by-id/idontexist'
        device = self.device_helper._dev_major_minor(path)
        self.assertIn(path, self.device_helper.non_existent_paths)
        self.assertEqual(device, None)

    def test_dev_major_minor_path_exists_retries(self):
        """ With existing path, method only calls stat once """
        path = '/dev/disk/by-id/adisk'
        self.stat_patcher.stop()
        mock_stat = mock.patch('os.stat', return_value=TestDeviceHelper.mock_devices[path]).start()
        self.device_helper._dev_major_minor(path)
        self.assertEqual(mock_stat.call_count, 1)
        self.assertNotIn(path, self.device_helper.non_existent_paths)

    def test_dev_major_minor_path_retry_doesnt_exist_retries(self):
        """
        Test non-existent path retries specified amount, and is subsequently added to the no-retry list.
        On the next attempt with the same path, there should be no retries.
        """
        path = '/dev/disk/by-id/idontexist'
        self.stat_patcher.stop()
        self.assertNotIn(path, self.device_helper.non_existent_paths)
        mock_stat = mock.patch('os.stat').start()
        mock_stat.side_effect = OSError(errno.ENOENT, 'No such file or directory.')
        self.device_helper._dev_major_minor(path)
        self.assertEqual(mock_stat.call_count, DeviceHelper.MAXRETRIES)
        self.assertIn(path, self.device_helper.non_existent_paths)
        mock_stat.reset_mock()
        self.device_helper._dev_major_minor(path)
        self.assertEqual(mock_stat.call_count, 1)
        self.assertIn(path, self.device_helper.non_existent_paths)

    def test_paths_to_major_minors_paths_exist(self):
        devices = self.device_helper._paths_to_major_minors(['/dev/disk/by-id/adisk'])
        self.assertEqual(len(devices), 1)

    def test_paths_to_major_minors_a_path_doesnt_exist(self):
        devices = self.device_helper._paths_to_major_minors(['/dev/disk/by-id/adisk', '/dev/disk/by-id/idontexist'])
        self.assertEqual(devices, [])
