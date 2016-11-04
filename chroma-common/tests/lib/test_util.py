import mock
from django.utils import unittest
from chroma_common.lib.util import PreserveFileAttributes


class PreservePermissionTestCase(unittest.TestCase):

    def test_file(self):
        for filename, st_mode, st_uid, st_gid in [('sidney', 493, 2, 10),
                                                  ('denver', 362, 4, 7),
                                                  ('shytown', 302, 5, 8)]:
            magic_stat_mock = mock.MagicMock()
            magic_stat_mock.st_mode = st_mode
            magic_stat_mock.st_uid = st_uid
            magic_stat_mock.st_gid = st_gid

            mock_os_stat = mock.patch('os.stat', return_value=magic_stat_mock).start()
            mock_os_chown = mock.patch('os.chown').start()
            mock_os_chmod = mock.patch('os.chmod').start()

            with PreserveFileAttributes(filename):
                self.assertEqual(mock_os_stat.call_count, 3)
                mock_os_stat.assert_called_with(filename)

            self.assertEqual(mock_os_chmod.call_count, 1)
            mock_os_chmod.assert_called_with(filename, magic_stat_mock.st_mode)
            self.assertEqual(mock_os_chown.call_count, 1)
            mock_os_chown.assert_called_with(filename, magic_stat_mock.st_uid, magic_stat_mock.st_gid)

            mock.patch.stopall()
