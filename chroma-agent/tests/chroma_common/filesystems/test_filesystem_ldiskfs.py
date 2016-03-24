import mock

from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand
from chroma_agent.chroma_common.filesystems.filesystem_ldiskfs import FileSystemLdiskfs


class TestFileSystemLdiskfs(CommandCaptureTestCase):
    def setUp(self):
        super(TestFileSystemLdiskfs, self).setUp()

        mock.patch.object(FileSystemLdiskfs, '_initialize_modules').start()

        self.filesystem = FileSystemLdiskfs('ldiskfs', '/dev/sda')

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def test_mount_fail_initial(self):
        """Test when initial mount fails, retry succeeds and result returned"""
        self.add_commands(CommandCaptureCommand(('mount', '-t', 'lustre', '/dev/sda', '/mnt/OST0000'), rc=5,
                                                executions_remaining=1),
                          CommandCaptureCommand(('mount', '-t', 'lustre', '/dev/sda', '/mnt/OST0000'), rc=0,
                                                executions_remaining=1))

        self.filesystem.mount('test_target_name', '/mnt/OST0000')

        self.assertRanAllCommandsInOrder()

    def test_mount_different_rc_fail_initial(self):
        """Test when initial mount fails and the rc doesn't cause a retry, exception is raised"""
        self.add_commands(CommandCaptureCommand(('mount', '-t', 'lustre', '/dev/sda', '/mnt/OST0000'), rc=1,
                                                executions_remaining=1))

        self.assertRaises(RuntimeError, self.filesystem.mount, 'test_target_name', '/mnt/OST0000')

        self.assertRanAllCommandsInOrder()

    def test_mount_fail_second(self):
        """Test when initial mount fails and the retry fails, exception is raised"""
        self.add_commands(CommandCaptureCommand(('mount', '-t', 'lustre', '/dev/sda', '/mnt/OST0000'), rc=5,
                                                executions_remaining=1),
                          CommandCaptureCommand(('mount', '-t', 'lustre', '/dev/sda', '/mnt/OST0000'), rc=5,
                                                executions_remaining=1))

        self.assertRaises(RuntimeError, self.filesystem.mount, 'test_target_name', '/mnt/OST0000')

        self.assertRanAllCommandsInOrder()
