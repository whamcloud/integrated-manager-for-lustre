import mock
from collections import namedtuple
from django.utils import unittest

import chroma_agent.chroma_common.lib.shell

CommandCaptureCommand = namedtuple("CommandCaptureCommand", ["args", "rc", "stdout", "stderr"])
CommandCaptureCommand.__new__.__defaults__ = ([], 0, '', '')


class CommandCaptureTestCase(unittest.TestCase):
    def setUp(self):
        self.reset_command_capture()
        self._err_msg = 'Command attempted was unknown to the CommandCaptureTestCase code, did you intend this?'

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
        '''
        return the command whose args match those given.
        :param args: Tuple of the arguments of the command
        :return: The command requested or raise a KeyError
        '''
        for command in self._commands:
            if command.args == args:
                return command

        raise KeyError

    def assertRanCommand(self, args):
        '''
        assert that the command made up of the args passed was executed.
        :param args: Tuple of the arguments of the command
        '''
        self._get_command(args)

    def assertRanAllCommandsInOrder(self):
        '''
        assert that all the commands expected were run in the order expected.
        '''
        self.assertEqual(len(self._commands), len(self._commands_history))

        for ran, expected_args in zip(self._commands, self._commands_history):
            self.assertEqual(ran.args, expected_args)

    def assertRanAllCommands(self):
        '''
        assert that all the commands expected were run, the order is not important.
        Some commands may be run more than once.
        '''
        commands_history = set(self._commands_history)

        self.assertEqual(len(self._commands), len(commands_history))

        for args in commands_history:
            self.assertRanCommand(args)

    def add_commands(self, *commands):
        '''
        Add a list of command that is expected to be run.
        :param *commands: CommandCaptureCommand args of commands to be run
        :return: No return value
        '''
        for command in commands:
            self._commands.append(command)

    def add_command(self, args, rc = 0, stdout = "", stderr = ""):
        '''
        Add a single command that is expected to be run.
        :param args: Tuple of the arguments of the command
        :param rc: return of the command
        :param stdout: stdout for the command
        :param stderr: stderr for the command
        :return: No return value
        '''
        self.add_commands(CommandCaptureCommand(args, rc, stdout, stderr))

    @property
    def commands_ran_count(self):
        return len(self._commands_history)

    def reset_command_capture(self):
        '''
        Reset the command capture to the initialized state.
        :return: None
        '''
        self._commands = []
        self.reset_command_capture_logs()

    def reset_command_capture_logs(self):
        '''
        Reset the command capture logs to the initialized state.
        :return: None
        '''
        self._commands_history = []
