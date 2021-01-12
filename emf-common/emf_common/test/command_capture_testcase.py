# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import mock
import errno

from emf_common.lib.shell import Shell
from emf_unit_testcase import EmfUnitTestCase


class CommandCaptureCommand(object):
    def __init__(self, args, rc=0, stdout="", stderr="", executions_remaining=99999999):
        self.args = args
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        self.executions_remaining = executions_remaining

    def __str__(self):
        return '"%s" returning %s' % (" ".join(self.args), self.rc)


class CommandCaptureTestCase(EmfUnitTestCase):
    CommandNotFound = 123456

    def setUp(self):
        super(CommandCaptureTestCase, self).setUp()

        self.reset_command_capture()
        self._missing_command_err_msg = (
            'Command attempted "%s" was unknown to CommandCaptureTestCase, did you intend this?'
        )

        assert "fake" not in str(Shell.run)
        mock.patch("emf_common.lib.shell.BaseShell.run", self._fake_run).start()

    def _fake_run(self, arg_list, logger=None, monitor_func=None, timeout=Shell.SHELLTIMEOUT, shell=False):
        assert type(arg_list) in [list, str, unicode], "arg list must be list or str :%s" % type(arg_list)

        # Allow simple commands to just be presented as a string. However do not start formatting the string this
        # will be rejected in a code review. If it has args present them as a list.
        if type(arg_list) in [str, unicode]:
            arg_list = arg_list.split()

        args = tuple(arg_list)
        self._commands_history.append(args)

        try:
            result = self._get_executable_command(args)
            result.executions_remaining -= 1

            if result.rc == self.CommandNotFound:
                raise OSError(errno.ENOENT, result.stderr)

            return Shell.RunResult(result.rc, result.stdout, result.stderr, False)
        except KeyError:
            raise OSError(errno.ENOENT, self._missing_command_err_msg % " ".join(arg_list))

    def _get_executable_command(self, args):
        """
        return the command whose args match those given. note that exact order match is needed

        FIXME: return more information about whether command was nearly correct compare each
        command in list, print the one that's closest rather than just 'no such...'

        :param args: Tuple of the arguments of the command
        :return: The command requested or raise a KeyError
        """
        for command in self._commands:
            if command.args == args and command.executions_remaining > 0:
                return command
        raise KeyError

    def assertRanCommand(self, command):
        """
        assert that the command made up of the args passed was executed.
        :param command: The command to check was run.
        """
        self.assertTrue(command.args in self._commands_history)

    def assertRanAllCommandsInOrder(self):
        """
        assert that all the commands expected were run in the order expected.
        """
        self.assertEqual(len(self._commands), len(self._commands_history))

        for ran, expected_args in zip(self._commands, self._commands_history):
            self.assertEqual(ran.args, expected_args)

    def assertRanAllCommands(self):
        """
        assert that all the commands expected were run, the order is not important.
        Some commands may be run more than once.
        """
        commands_history = set(self._commands_history)

        self.assertEqual(len(self._commands), len(commands_history))

        for command in self._commands:
            self.assertRanCommand(command)

    def add_commands(self, *commands):
        """
        Add a list of command that is expected to be run.
        :param *commands: CommandCaptureCommand args of commands to be run
        :return: No return value
        """
        for command in commands:
            self._commands.append(command)

    def single_commands(self, *commands):
        """
        Add a list of commands that are expected to be run only once.
        :param *commands: CommandCaptureCommand args of commands to be run once
        :return: No return value
        """
        for command in commands:
            command.executions_remaining = 1
            self._commands.append(command)

    def add_command(self, args, rc=0, stdout="", stderr="", executions_remaining=99999999):
        """
        Add a single command that is expected to be run.
        :param args: Tuple of the arguments of the command
        :param rc: return of the command
        :param stdout: stdout for the command
        :param stderr: stderr for the command
        :return: No return value
        """
        self.add_commands(CommandCaptureCommand(args, rc, stdout, stderr, executions_remaining))

    @property
    def commands_ran_count(self):
        return len(self._commands_history)

    def reset_command_capture(self):
        """
        Reset the command capture to the initialized state.
        :return: None
        """
        self._commands = []
        self.reset_command_capture_logs()

    def reset_command_capture_logs(self):
        """
        Reset the command capture logs to the initialized state.
        :return: None
        """
        self._commands_history = []
