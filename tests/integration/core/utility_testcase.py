import inspect
import logging
import paramiko
import os
import subprocess
import time
import socket
import threading

from django.utils.unittest import TestCase
from testconfig import config

from tests.integration.core.constants import TEST_TIMEOUT

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(os.path.join(config.get("log_dir", "/var/log/"), "chroma_test.log"))
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# paramiko.transport logger spams nose log collection so we're quieting it down
paramiko_logger = logging.getLogger("paramiko.transport")
paramiko_logger.setLevel(logging.WARN)


class ExceptionThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ExceptionThread, self).__init__(*args, **kwargs)
        self._exception_value = None

    def run(self):
        try:
            return super(ExceptionThread, self).run()
        except BaseException as e:
            self._exception_value = e

    def join(self):
        super(ExceptionThread, self).join()
        if self._exception_value:
            raise self._exception_value


class RemoteCommandResult(object):
    """
    Conveniently stores the various output of a remotely executed command.
    """

    def __init__(self, exit_status, stdout, stderr, *args, **kwargs):
        super(RemoteCommandResult, self).__init__(*args, **kwargs)
        self.exit_status = exit_status
        self.stdout = stdout
        self.stderr = stderr


class UtilityTestCase(TestCase):
    """Adds a few non-api specific utility functions for the integration tests.
    """

    # Allows us to not fetch help repeatedly for the same error buy keeping track of
    # those things we have fetched help for.
    help_fetched_list = []

    def setUp(self):
        self.maxDiff = None  # By default show the complete diff on errors.

    def execute_commands(self, commands, target, debug_message, expected_return_code=0):
        stdout = []
        for command in commands:
            result = self.remote_command(target, command, expected_return_code=expected_return_code)
            logger.info(
                "%s command %s exit_status %s \noutput:\n %s \nstderr:\n %s"
                % (debug_message, command, result.exit_status, result.stdout, result.stderr)
            )

            stdout.append(result.stdout)

        return stdout

    def execute_simultaneous_commands(self, commands, targets, debug_message, expected_return_code=0):
        threads = []
        for target in targets:
            command_thread = ExceptionThread(
                target=self.execute_commands,
                args=(commands, target, "%s: %s" % (target, debug_message), expected_return_code),
            )
            command_thread.start()
            threads.append(command_thread)

        map(lambda th: th.join(), threads)

    def remote_command(self, server, command, expected_return_code=0, timeout=TEST_TIMEOUT):
        """
        Executes a command on a remote server over ssh.

        Sends a command over ssh to a remote machine and returns the stdout,
        stderr, and exit status. It will verify that the exit status of the
        command matches expected_return_code unless expected_return_code=None.

        FIXME: Extreme redundancy with _ssh_address in RealRemoteOperations.
        """
        logger.debug("remote_command[%s]: %s" % (server, command))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, **{"username": "root"})
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(timeout)
        # exec 0<&- being prefixed to the shell command string below closes
        # the shell's stdin as we don't expect any uses of remote_command()
        # to read from stdin
        # the set -e just sets up a fail-safe execution environment where
        # any shell commands in command that fail and are not error checked
        # cause the shell to fail, alerting the caller that one of their
        # commands failed unexpectedly
        channel.exec_command("exec 0<&-; set -e; %s" % command)
        exit_status = channel.recv_exit_status()
        stdout = channel.makefile("rb").read()
        stderr = channel.makefile_stderr("rb").read()
        if expected_return_code is not None:
            self.assertEqual(exit_status, expected_return_code, stderr)
        return RemoteCommandResult(exit_status, stdout, stderr)

    def wait_until_true(self, lambda_expression, error_message="", timeout=TEST_TIMEOUT):
        """Evaluates lambda_expression once/1s until True or hits timeout."""
        assert hasattr(lambda_expression, "__call__"), "lambda_expression is not callable: %s" % type(lambda_expression)
        assert (
            hasattr(error_message, "__call__") or type(error_message) is str
        ), "error_message is not callable and not a str: %s" % type(error_message)
        assert type(timeout) == int, "timeout is not an int: %s" % type(timeout)

        running_time = 0
        lambda_result = None
        wait_time = 0.01
        while not lambda_result and running_time < timeout:
            lambda_result = lambda_expression()
            logger.debug("%s evaluated to %s" % (inspect.getsource(lambda_expression), lambda_result))

            if not lambda_result:
                time.sleep(wait_time)
                wait_time = min(1, wait_time * 10)
                running_time += wait_time

        if hasattr(error_message, "__call__"):
            error_message = error_message()

        self.assertLess(
            running_time,
            timeout,
            "Timed out waiting for %s\nError Message %s" % (inspect.getsource(lambda_expression), error_message),
        )

    def wait_for_items_length(self, fetch_items, length, timeout=TEST_TIMEOUT):
        """
        Assert length of items list generated by func over time or till timeout.
        """
        items = fetch_items()
        while timeout and length != len(items):
            logger.debug(
                "%s evaluated to %s expecting list size of %s items" % (inspect.getsource(fetch_items), items, length)
            )
            time.sleep(1)
            timeout -= 1
            items = fetch_items()
        self.assertNotEqual(0, timeout, "Timed out waiting for %s." % inspect.getsource(fetch_items))

    def wait_for_assert(self, lambda_expression, timeout=TEST_TIMEOUT):
        """
        Evaluates lambda_expression once/1s until no AssertionError or hits
        timeout.
        """
        running_time = 0
        assertion = None
        while running_time < timeout:
            try:
                lambda_expression()
            except AssertionError as e:
                assertion = e
                logger.debug("%s tripped assertion: %s" % (inspect.getsource(lambda_expression), e))
            else:
                break
            time.sleep(1)
            running_time += 1
        self.assertLess(
            running_time,
            timeout,
            "Timed out waiting for %s\nAssertion %s" % (inspect.getsource(lambda_expression), assertion),
        )

    def get_host_config(self, nodename):
        """
        Get the entry for a lustre server from the cluster config.
        """
        for host in config["lustre_servers"]:
            if host["nodename"] == nodename:
                return host

    def _fetch_help(self, assert_test, tell_who, message=None, callback=lambda: True, timeout=1800):
        """When an error occurs that we want to hold the cluster for until someone logs in then this function will do that.

        The file /tmp/waiting_help is used as an exit switch along with time. Deleting this file will cause the test to
        continue running - actually raising the exception in fact. This file is also used to put the message in.

        :param assert_test: test that if it occurs will fetch the help
        :param callback: optional but if present returning False will cause the routine to not fetch help.
        :param tell_who: list of email addresses to contact about the issue
        :param message: message to deliver to those people, can be a callable returning a string, or None to use the exception.
        :param timeout: How long to wait before continuing.
        :return: None

        Typical usage.
        self._fetch_help(lambda: self.assertEqual(commandResult, True),
                         ['joe.grund@intel.com', 'tom.nabarro@intel.com', 'william.c.johnson@intel.com'],
                         'Send the cavalry',
                         callback=lambda: check_if_significant(data))

        self._fetch_help(lambda: self.assertEqual(commandResult, True),
                         ['joe.grund@intel.com', 'tom.nabarro@intel.com', 'william.c.johnson@intel.com'],
                         lambda: 'Send the cavalry',
                         callback=lambda: check_if_significant(data))

        """

        try:
            return assert_test()
        except Exception as exception:
            if callback() == False or assert_test in self.help_fetched_list:
                raise

            self.help_fetched_list.append(assert_test)

            key_file = "/tmp/waiting_help"

            if message is None:
                message = str(exception)
            elif hasattr(message, "__call__"):
                message = message()

            # First create the file, errors in here do destroy the original, but will be reported by the test framework
            fd = os.open(key_file, os.O_RDWR | os.O_CREAT)
            os.write(
                fd,
                "To: %s\nSubject: %s\n\n%s\n\nTest Runner %s"
                % (", ".join(tell_who), message, message, socket.gethostname()),
            )
            os.lseek(fd, 0, os.SEEK_SET)
            subprocess.call(["sendmail"] + ["-t"], stdin=fd)
            os.close(fd)

            while timeout > 0 and os.path.isfile(key_file):
                timeout -= 1
                time.sleep(1)

            raise
