import mock
from os import environ
from iml_common.lib import util
from iml_common.test.iml_unit_testcase import ImlUnitTestCase


def target_func():
    return


class PreservePermissionTestCase(ImlUnitTestCase):
    def test_file(self):
        for filename, st_mode, st_uid, st_gid in [
            ("sidney", 493, 2, 10),
            ("denver", 362, 4, 7),
            ("shytown", 302, 5, 8),
        ]:
            magic_stat_mock = mock.MagicMock()
            magic_stat_mock.st_mode = st_mode
            magic_stat_mock.st_uid = st_uid
            magic_stat_mock.st_gid = st_gid

            mock_os_stat = mock.patch("os.stat", return_value=magic_stat_mock).start()
            mock_os_chown = mock.patch("os.chown").start()
            mock_os_chmod = mock.patch("os.chmod").start()

            with util.PreserveFileAttributes(filename):
                self.assertEqual(mock_os_stat.call_count, 3)
                mock_os_stat.assert_called_with(filename)

            self.assertEqual(mock_os_chmod.call_count, 1)
            mock_os_chmod.assert_called_with(filename, magic_stat_mock.st_mode)
            self.assertEqual(mock_os_chown.call_count, 1)
            mock_os_chown.assert_called_with(filename, magic_stat_mock.st_uid, magic_stat_mock.st_gid)


class DisableThreadsTestCase(ImlUnitTestCase):
    def setUp(self):
        super(DisableThreadsTestCase, self).setUp()
        environ.pop("IML_DISABLE_THREADS", None)

    def tearDown(self):
        environ.pop("IML_DISABLE_THREADS", None)
        super(DisableThreadsTestCase, self).tearDown()

    def test_threads_on(self):
        thread = util.ExceptionThrowingThread(target=target_func, args=())

        self.assertTrue(thread._use_threads)

    def test_threads_on_values(self):
        values = ["0", ""]
        for value in values:
            environ["IML_DISABLE_THREADS"] = value
            thread = util.ExceptionThrowingThread(target=target_func, args=())

            self.assertTrue(thread._use_threads)

    def test_threads_off(self):
        environ["IML_DISABLE_THREADS"] = "1"
        thread = util.ExceptionThrowingThread(target=target_func, args=())

        self.assertFalse(thread._use_threads)
