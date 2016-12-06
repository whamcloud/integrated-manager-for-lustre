import time
import threading
import mock
from collections import defaultdict

from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import ZfsDevice
from tests.command_capture_testcase import CommandCaptureCommand
from tests.command_capture_testcase import CommandCaptureTestCase
from chroma_agent.chroma_common.lib.util import ExceptionThrowingThread
from chroma_agent.chroma_common.lib.shell import BaseShell


class TestZfsDevice(CommandCaptureTestCase):
    def setUp(self):
        super(TestZfsDevice, self).setUp()

        self.zpool_name = 'Dave'

        # Reset the locks or 1 test failing kills all the other.s
        ZfsDevice.import_locks = defaultdict(lambda: threading.RLock())

        self.lock = ZfsDevice.import_locks[self.zpool_name]
        self.thread_running = False

        self.assertEqual(type(self.lock), threading._RLock)

    def _add_import_commands(self, name='Boris'):
        self.add_commands(CommandCaptureCommand(('zpool', 'list', '-H', '-o', 'name'), stdout=name))

        if name != self.zpool_name:
            self.add_commands(CommandCaptureCommand(('zpool', 'import', '-f', '-o', 'readonly=on', self.zpool_name)))

    def _add_export_commands(self):
        self.add_commands(CommandCaptureCommand(('zpool', 'export', self.zpool_name)))

    def test_import(self):
        for force in [True, False]:
            for readonly in [True, False]:
                self.reset_command_capture()

                self.add_commands(CommandCaptureCommand(('zpool', 'import') +
                                                        (('-f',) if force else ()) +
                                                        (('-o', 'readonly=on') if readonly else ()) +
                                                        (self.zpool_name,)))

                ZfsDevice(self.zpool_name, False).import_(force, readonly)

                self.assertRanAllCommandsInOrder()

    def test_import_writable(self):
        self._add_import_commands()
        self._add_export_commands()

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)
        exported_zfs_device.__exit__(0, 0, 0)

        self.assertRanAllCommandsInOrder()

    def test_simple_lock(self):
        self._add_import_commands()
        self._add_export_commands()

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)
        self.assertEqual(self.lock._RLock__count, 1)

        exported_zfs_device.__exit__(0, 0, 0)
        self.assertEqual(self.lock._RLock__count, 0)

        self.assertRanAllCommandsInOrder()

    def test_simple_multiple_entry_lock(self):
        exported_zfs_devices = []

        for count in range(1, 10):
            self._add_import_commands()
            exported_zfs_devices.insert(0, ZfsDevice(self.zpool_name, True))
            self.assertEqual(exported_zfs_devices[0].__enter__().available, True)
            self.assertEqual(self.lock._RLock__count, count)

        for count in range(9, 0, -1):
            self._add_export_commands()
            exported_zfs_devices[0].__exit__(0, 0, 0)
            del exported_zfs_devices[0]
            self.assertEqual(self.lock._RLock__count, count - 1)

        self.assertEqual(self.lock._RLock__count, 0)
        self.assertRanAllCommandsInOrder()

    def test_simple_lock_no_import(self):
        self._add_import_commands(self.zpool_name)

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)
        self.assertEqual(self.lock._RLock__count, 1)

        exported_zfs_device.__exit__(0, 0, 0)
        self.assertEqual(self.lock._RLock__count, 0)

        self.assertRanAllCommandsInOrder()

    def import_(self):
        self.add_command(('zpool', 'import', self.zpool_name))
        self.thread_running = True
        ZfsDevice(self.zpool_name, True).import_(False, False)
        self.thread_running = False

    def export(self):
        self._add_export_commands()
        self.thread_running = True
        ZfsDevice(self.zpool_name, True).export()
        self.thread_running = False

    def test_import_blocks(self):
        self._add_import_commands()
        self._add_export_commands()

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)
        self.assertEqual(self.lock._RLock__count, 1)

        # Now this thread should block.
        thread = ExceptionThrowingThread(target=self.import_,
                                         args=(),
                                         use_threads=True)
        thread.start()

        time.sleep(0.1)
        self.assertEqual(self.thread_running, True)
        time.sleep(0.1)
        self.assertEqual(self.thread_running, True)

        exported_zfs_device.__exit__(0, 0, 0)

        time.sleep(0.1)
        self.assertEqual(self.thread_running, False)

        self.assertEqual(self.lock._RLock__count, 0)

        thread.join()

    def test_export_blocks(self):
        self._add_import_commands()
        self._add_export_commands()

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)
        self.assertEqual(self.lock._RLock__count, 1)

        # Now this thread should block.
        thread = ExceptionThrowingThread(target=self.export,
                                         args=(),
                                         use_threads=True)
        thread.start()

        time.sleep(0.1)
        self.assertEqual(self.thread_running, True)
        time.sleep(0.1)
        self.assertEqual(self.thread_running, True)

        exported_zfs_device.__exit__(0, 0, 0)

        time.sleep(0.1)
        self.assertEqual(self.thread_running, False)

        self.assertEqual(self.lock._RLock__count, 0)

        thread.join()

    def test_error_in_list(self):
        self.add_commands(CommandCaptureCommand(('zpool', 'list', '-H', '-o', 'name'), rc=1))

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        try:
            self.assertEqual(exported_zfs_device.__enter__(), True)
        except BaseShell.CommandExecutionError:
            pass

        self.assertEqual(self.lock._RLock__count, 0)

    def test_error_in_import(self):
        self.add_commands(CommandCaptureCommand(('zpool', 'list', '-H', '-o', 'name'), stdout='Boris'),
                          CommandCaptureCommand(('zpool', 'import', '-f', '-o', 'readonly=on', self.zpool_name), rc=1))

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, False)

        self.assertEqual(self.lock._RLock__count, 1)

        exported_zfs_device.__exit__(0, 0, 0)

        self.assertEqual(self.lock._RLock__count, 0)

        self.assertRanAllCommandsInOrder()

    def test_error_in_export(self):
        self._add_import_commands()
        self.add_commands(CommandCaptureCommand(('zpool', 'export', self.zpool_name), rc=1))

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)

        self.assertEqual(self.lock._RLock__count, 1)

        try:
            exported_zfs_device.__exit__(0, 0, 0)
        except BaseShell.CommandExecutionError:
            pass

        self.assertEqual(self.lock._RLock__count, 0)

        self.assertRanAllCommandsInOrder()

    def test_busy_export(self):
        self._add_import_commands()
        self.add_commands(CommandCaptureCommand(('zpool', 'export', self.zpool_name),
                                                rc=1,
                                                stderr="cannot export '%s': pool is busy" % self.zpool_name,
                                                executions_remaining=1))
        self._add_export_commands()

        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.time.sleep').start()

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

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

        exported_zfs_device = ZfsDevice(self.zpool_name, True)

        self.assertEqual(exported_zfs_device.__enter__().available, True)

        try:
            exported_zfs_device.__exit__(0, 0, 0)
        except BaseShell.CommandExecutionError:
            pass

    def test_no_import_silient(self):
        exported_zfs_device = ZfsDevice(self.zpool_name, False)

        self.assertEqual(exported_zfs_device.available, True)
        self.assertEqual(exported_zfs_device.__enter__().available, True)
        exported_zfs_device.__exit__(0, 0, 0)

        self.assertRanAllCommandsInOrder()
