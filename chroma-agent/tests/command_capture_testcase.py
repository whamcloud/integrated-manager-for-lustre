import mock
from django.utils import unittest

from chroma_agent.chroma_common.lib.shell import Shell


class CommandCaptureCommand(object):
    def __init__(self, args, rc=0, stdout='', stderr='', executions_remaining=99999999):
        self.args = args
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        self.executions_remaining = executions_remaining


class CommandCaptureTestCase(unittest.TestCase):
    def setUp(self):
        self.reset_command_capture()
        self._missing_command_err_msg = 'Command attempted was unknown to CommandCaptureTestCase, did you intend this?'

        assert 'fake' not in str(Shell.run)
        mock.patch('chroma_agent.chroma_common.lib.shell.Shell.run', self._fake_run).start()

        self.addCleanup(mock.patch.stopall)

    def _fake_run(self, arg_list, logger=None, monitor_func=None, timeout=Shell.SHELLTIMEOUT):
            args = tuple(arg_list)
            self._commands_history.append(args)

            try:
                result = self._get_executable_command(args)
                result.executions_remaining -= 1

                return Shell.RunResult(result.rc, result.stdout, result.stderr, False)
            except KeyError:
                return Shell.RunResult(2, "", self._missing_command_err_msg, False)

    def _get_executable_command(self, args):
        '''
        return the command whose args match those given. note that exact order match is needed

        FIXME: return more information about whether command was nearly correct compare each
        command in list, print the one that's closest rather than just 'no such...'

        :param args: Tuple of the arguments of the command
        :return: The command requested or raise a KeyError
        '''
        for command in self._commands:
            if command.args == args and command.executions_remaining > 0:
                return command
        raise KeyError

    def assertRanCommand(self, args):
        '''
        assert that the command made up of the args passed was executed.
        :param args: Tuple of the arguments of the command
        '''
        self._get_executable_command(args)

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

    def add_command(self, args, rc = 0, stdout = "", stderr = "", executions_remaining=99999999):
        '''
        Add a single command that is expected to be run.
        :param args: Tuple of the arguments of the command
        :param rc: return of the command
        :param stdout: stdout for the command
        :param stderr: stderr for the command
        :return: No return value
        '''
        self.add_commands(CommandCaptureCommand(args, rc, stdout, stderr, executions_remaining))

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
