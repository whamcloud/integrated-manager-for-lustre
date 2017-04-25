import os
import shutil
import mock
import time

from collections import defaultdict
from lockfile import LockFile


from tests.command_capture_testcase import CommandCaptureCommand
from tests.command_capture_testcase import CommandCaptureTestCase
from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import ZfsDevice
from chroma_agent.chroma_common.lib.util import ExceptionThrowingThread
from chroma_agent.chroma_common.lib.shell import BaseShell

TEST_ZPOOL_LOCK_DIR = '/tmp/chroma-agent-test-locks'
TEST_LOCK_ACQUIRE_TIMEOUT = 1


class TestZfsDevice(CommandCaptureTestCase):
    def setUp(self):
        super(TestZfsDevice, self).setUp()

        self.zpool_name = 'Dave'

        self.addCleanup(mock.patch.stopall)

    def _add_import_commands(self, name='Boris'):
        self.add_commands(CommandCaptureCommand(('zpool', 'list', '-H', '-o', 'name'), stdout=name))

        if name != self.zpool_name:
            self.add_commands(CommandCaptureCommand(('zpool', 'import', '-f', '-N', '-o', 'readonly=on', '-o', 'cachefile=none', self.zpool_name)))

    def _add_export_commands(self):
        self.add_commands(CommandCaptureCommand(('zpool', 'export', self.zpool_name)))

    @staticmethod
    def _get_zfs_device(name, try_import):
        device = ZfsDevice(name, try_import)
        device.lock_unique_id = 'mockhost_mockthread.mockpid:%s' % name
        return device


class TestZfsDeviceImportExport(TestZfsDevice):
    def setUp(self):
        super(TestZfsDeviceImportExport, self).setUp()

        class MockLockFile(LockFile):
            # add attributes to mock that would be created at runtime and therefore cannot be autospecced
            unique_name = None
            pid = 12345

        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.LockFile', autospec=MockLockFile).start()

        ZfsDevice.lock_refcount = defaultdict(int)
        self.zfs_device = ZfsDevice(self.zpool_name, False)
        self.zfs_device.lock_unique_id = 'mockhost_mockthread.mockpid:%s' % self.zpool_name
        self.zfs_device.lock.path = '%s/%s' % (ZfsDevice.ZPOOL_LOCK_DIR, self.zpool_name)
        self.zfs_device.lock.reset_mock()

        self.zfs_device.lock.acquire.return_value = None
        self.zfs_device.lock.acquire.side_effect = self._toggle_lock
        self.zfs_device.lock.release.return_value = None
        self.zfs_device.lock.release.side_effect = self._toggle_lock
        self.zfs_device.lock.is_locked.return_value = False
        self.zfs_device.lock.i_am_locking.return_value = False

    def _toggle_lock(self, timeout=0):
        self.zfs_device.lock.i_am_locking.return_value ^= True
        self.zfs_device.lock.is_locked.return_value ^= True

    def _acquire_returns(self, timeout=0):
        self.idx += 1
        try:
            raise self.acquire_actions[self.idx]
        except TypeError:
            self.acquire_actions[self.idx](self)

    def test_import(self):
        for force in [True, False]:
            for readonly in [True, False]:
                self.reset_command_capture()

                self.add_commands(CommandCaptureCommand(('zpool', 'import') +
                                                        (('-f',) if force else ()) +
                                                        (('-N', '-o', 'readonly=on', '-o', 'cachefile=none') if readonly else ()) +
                                                        (self.zpool_name,)))

                self.zfs_device.import_(force, readonly)

                self.zfs_device.lock.acquire.assert_called_once_with(ZfsDevice.LOCK_ACQUIRE_TIMEOUT)
                self.zfs_device.lock.release.assert_called_once_with()
                self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)

                self.assertRanAllCommandsInOrder()
                self.zfs_device.lock.reset_mock()

    # def test_import_locked(self):
    #     self.reset_command_capture()
    #
    #     self.zfs_device.lock.acquire.side_effect = LockTimeout
    #
    #     with self.assertRaises(LockTimeout):
    #         self.zfs_device.import_(False, False)
    #
    #     self.assertEqual(self.zfs_device.lock.acquire.call_count,
    #                      (ZPOOL_LOCK_TIMEOUT / LOCK_ACQUIRE_TIMEOUT) + 1)
    #
    #     self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), None)
    #     self.assertEqual(self.zfs_device.lock.release.call_count, 0)
    #     self.assertEqual(self.zfs_device.lock.break_lock.call_count, 0)
    #
    #     self.assertRanAllCommandsInOrder()

    # def test_import_force_locked(self):
    #     self.reset_command_capture()
    #
    #     self.add_commands(CommandCaptureCommand(('zpool', 'import', '-f', '-N', '-o', 'readonly=on', '-o',
    #                                              'cachefile=none', self.zpool_name,)))
    #
    #     # simulate 2 lock timeouts and then a successful lock acquire as side effects
    #     self.idx = -1
    #     self.acquire_actions = (LockTimeout, self._toggle_lock)
    #     self.zfs_device.lock.acquire.side_effect = self._acquire_returns
    #
    #     self.zfs_device.import_(True, True, True)
    #
    #     delattr(self, 'acquire_actions')
    #     delattr(self, 'idx')
    #
    #     self.zfs_device.lock.acquire.assert_has_calls([mock.call(LOCK_ACQUIRE_TIMEOUT),
    #                                                    mock.call(LOCK_ACQUIRE_TIMEOUT)])
    #
    #     self.zfs_device.lock.break_lock.assert_called_once_with()
    #     self.zfs_device.lock.release.assert_called_once_with()
    #     self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)
    #
    #     self.assertRanAllCommandsInOrder()

    def test_import_writable(self):
        self._add_import_commands()
        self._add_export_commands()

        self.assertFalse(self.zfs_device.try_import)
        self.zfs_device.try_import = True

        self.assertTrue(self.zfs_device.__enter__().available)

        self.assertTrue(self.zfs_device.lock.i_am_locking())
        self.assertTrue(self.zfs_device.pool_imported)
        self.assertTrue(self.zfs_device.available)
        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 1)

        self.zfs_device.__exit__(0, 0, 0)

        self.assertFalse(self.zfs_device.pool_imported)
        self.assertFalse(self.zfs_device.lock.i_am_locking())
        self.assertFalse(self.zfs_device.pool_imported)
        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)

        self.assertRanAllCommandsInOrder()

    def test_simple_multiple_entry_lock(self):
        exported_zfs_devices = []

        for count in range(1, 10):
            self._add_import_commands()
            exported_zfs_devices.insert(0, self._get_zfs_device(self.zpool_name, True))
            self.assertEqual(exported_zfs_devices[0].__enter__().available, True)
            self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), count)
            self.assertTrue(exported_zfs_devices[0].lock.i_am_locking())
            self.assertTrue(exported_zfs_devices[0].pool_imported)

        for count in range(9, 0, -1):
            self._add_export_commands()
            exported_zfs_devices[0].__exit__(0, 0, 0)
            self.assertFalse(exported_zfs_devices[0].pool_imported)
            self.assertEqual(exported_zfs_devices[0].lock.i_am_locking(),
                             True if ((count - 1) > 0) else False)
            self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), count - 1)
            del exported_zfs_devices[0]

        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)
        self.assertFalse(ZfsDevice(self.zpool_name, True).lock.is_locked())

        self.assertRanAllCommandsInOrder()

    def test_simple_lock_no_import(self):
        self._add_import_commands(self.zpool_name)

        exported_zfs_device = self._get_zfs_device(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)
        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 1)
        self.assertTrue(exported_zfs_device.lock.i_am_locking())
        self.assertFalse(exported_zfs_device.pool_imported)

        exported_zfs_device.__exit__(0, 0, 0)
        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)
        self.assertFalse(exported_zfs_device.lock.i_am_locking())
        self.assertFalse(exported_zfs_device.pool_imported)

        self.assertRanAllCommandsInOrder()

    def test_error_in_list(self):
        self.add_commands(CommandCaptureCommand(('zpool', 'list', '-H', '-o', 'name'), rc=1))

        exported_zfs_device = self._get_zfs_device(self.zpool_name, True)

        with self.assertRaises(BaseShell.CommandExecutionError):
            exported_zfs_device.__enter__()

        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)
        self.assertFalse(exported_zfs_device.lock.i_am_locking())
        self.assertFalse(exported_zfs_device.pool_imported)
        self.assertFalse(exported_zfs_device.available)

        self.assertRanAllCommandsInOrder()

    def test_error_in_import(self):
        self.add_commands(CommandCaptureCommand(('zpool', 'list', '-H', '-o', 'name'), stdout='Boris'),
                          CommandCaptureCommand(('zpool', 'import', '-f', '-N', '-o', 'readonly=on', '-o', 'cachefile=none',
                                                 self.zpool_name), rc=1))

        exported_zfs_device = self._get_zfs_device(self.zpool_name, True)

        self.assertFalse(exported_zfs_device.__enter__().available)

        self.assertFalse(exported_zfs_device.pool_imported)
        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 1)

        exported_zfs_device.__exit__(0, 0, 0)

        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)

        self.assertRanAllCommandsInOrder()

    def test_error_in_export(self):
        self._add_import_commands()
        self.add_commands(CommandCaptureCommand(('zpool', 'export', self.zpool_name), rc=1))

        exported_zfs_device = self._get_zfs_device(self.zpool_name, True)

        self.assertTrue(exported_zfs_device.__enter__().available)

        self.assertTrue(exported_zfs_device.pool_imported)
        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 1)

        with self.assertRaises(BaseShell.CommandExecutionError):
            exported_zfs_device.__exit__(0, 0, 0)

        self.assertEqual(ZfsDevice.lock_refcount.get(self.zfs_device.lock_unique_id), 0)

        self.assertRanAllCommandsInOrder()

    def test_busy_export(self):
        self._add_import_commands()
        self.add_commands(CommandCaptureCommand(('zpool', 'export', self.zpool_name),
                                                rc=1,
                                                stderr="cannot export '%s': pool is busy" % self.zpool_name,
                                                executions_remaining=1))
        self._add_export_commands()

        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.time.sleep').start()

        exported_zfs_device = self._get_zfs_device(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)
        exported_zfs_device.__exit__(0, 0, 0)

        self.assertRanAllCommandsInOrder()

    def test_very_busy_export(self):
        self._add_import_commands()
        self.add_commands(CommandCaptureCommand(('zpool', 'export', self.zpool_name),
                                                rc=1,
                                                stderr="cannot export '%s': pool is busy" % self.zpool_name))
        self._add_export_commands()

        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.time.sleep').start()

        exported_zfs_device = self._get_zfs_device(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)

        with self.assertRaises(BaseShell.CommandExecutionError):
            exported_zfs_device.__exit__(0, 0, 0)

    def test_no_import_silent(self):
        exported_zfs_device = self._get_zfs_device(self.zpool_name, False)

        self.assertEqual(exported_zfs_device.available, True)
        self.assertEqual(exported_zfs_device.__enter__().available, True)
        self.assertFalse(exported_zfs_device.pool_imported)
        exported_zfs_device.__exit__(0, 0, 0)

        self.assertRanAllCommandsInOrder()


class TestZfsDeviceLockFile(TestZfsDevice):
    def setUp(self):
        super(TestZfsDeviceLockFile, self).setUp()

        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.ZfsDevice.ZPOOL_LOCK_DIR',
                   TEST_ZPOOL_LOCK_DIR).start()
        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.ZfsDevice.LOCK_ACQUIRE_TIMEOUT',
                   TEST_LOCK_ACQUIRE_TIMEOUT).start()

        self.zpool_name = 'Dave'
        self.thread_running = False

        shutil.rmtree(ZfsDevice.ZPOOL_LOCK_DIR, ignore_errors=True)
        os.mkdir(ZfsDevice.ZPOOL_LOCK_DIR)

    def tearDown(self):
        shutil.rmtree(ZfsDevice.ZPOOL_LOCK_DIR, ignore_errors=True)

    def import_(self):
        self.add_command(('zpool', 'import', self.zpool_name))
        self.thread_running = True
        zfs_device = ZfsDevice(self.zpool_name, False)
        zfs_device.import_(False, False)
        self.assertFalse(zfs_device.lock.i_am_locking())
        self.thread_running = False

    def export(self):
        self._add_export_commands()
        self.thread_running = True
        ZfsDevice(self.zpool_name, False).export()
        self.thread_running = False

    def _blocking_test_base(self, target_func):
        self._add_import_commands()
        self._add_export_commands()

        exported_zfs_device = ZfsDevice(self.zpool_name, True)
        self.assertEqual(exported_zfs_device.lock_unique_id, '%s:%s' % (exported_zfs_device.lock.unique_name,
                                                                        self.zpool_name))

        self.assertTrue(exported_zfs_device.__enter__().available)
        self.assertEqual(ZfsDevice.lock_refcount.get(exported_zfs_device.lock_unique_id), 1)
        self.assertTrue(exported_zfs_device.lock.i_am_locking())
        self.assertTrue(exported_zfs_device.pool_imported)

        # Now this thread should block.
        thread = ExceptionThrowingThread(target=target_func,
                                         args=(),
                                         use_threads=True)
        thread.start()

        time.sleep(0.1)
        self.assertEqual(self.thread_running, True)
        time.sleep(0.1)
        self.assertEqual(self.thread_running, True)

        self.assertEqual(ZfsDevice.lock_refcount.get(exported_zfs_device.lock_unique_id), 1)

        exported_zfs_device.__exit__(0, 0, 0)
        self.assertFalse(exported_zfs_device.lock.i_am_locking())
        self.assertFalse(exported_zfs_device.pool_imported)

        thread.join()

        time.sleep(0.1)
        self.assertEqual(self.thread_running, False)

    def test_import_blocks(self):
        self._blocking_test_base(self.import_)

    def test_export_blocks(self):
        self._blocking_test_base(self.export)
