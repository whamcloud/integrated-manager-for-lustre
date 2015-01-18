import mock
from collections import namedtuple
from django.utils import unittest

import chroma_agent.chroma_common.lib.shell

CommandCaptureCommand = namedtuple("CommandCaptureCommand", ["args", "rc", "stdout", "stderr"])
CommandCaptureCommand.__new__.__defaults__ = ([], 0, '', '')


class CommandCaptureTestCase(unittest.TestCase):
    def setUp(self):
        self._commands = []
        self._commands_history = []

        def fake_try_run(args):
            args = tuple(args)
            self._commands_history.append(args)

            try:
                result = self._get_command(args)
                if type(result) == str:
                    return result
                else:
                    if result.rc:
                        raise chroma_agent.chroma_common.lib.shell.CommandExecutionError(result.rc,
                                                                                         args,
                                                                                         result.stdout,
                                                                                         result.stderr)
                    return result.stdout
            except KeyError:
                raise OSError(2, 'No such file or directory', args[0])

        assert 'fake' not in str(chroma_agent.chroma_common.lib.shell.try_run)
        mock.patch('chroma_agent.chroma_common.lib.shell.try_run', fake_try_run).start()

        def fake_run(args):
            args = tuple(args)
            self._commands_history.append(args)

            try:
                result = self._get_command(args)

                return result.rc, result.stdout, result.stderr
            except KeyError:
                return (2, "", 'No such file or directory')

        mock.patch('chroma_agent.chroma_common.lib.shell.run', fake_run).start()

        self.addCleanup(mock.patch.stopall)

    def _get_command(self, args):
        for command in self._commands:
            if command.args == args:
                return command

        raise KeyError

    def assertRanCommand(self, args):
        self._get_command(args)

    def assertRanAllCommandsInOrder(self):
        self.assertEqual(len(self._commands), len(self._commands_history))

        for ran, expected_args in zip(self._commands, self._commands_history):
            self.assertEqual(ran.args, expected_args)

    def assertRanAllCommands(self):
        self.assertEqual(len(self._commands), len(self._commands_history))

        for args in self._commands_history:
            self.assertRanCommand(args)

    def add_commands(self, *commands):
        for command in commands:
            self._commands.append(command)

    def add_command(self, args, rc = 0, stdout = "", stderr = ""):
        self.add_commands(CommandCaptureCommand(args, rc, stdout, stderr))
