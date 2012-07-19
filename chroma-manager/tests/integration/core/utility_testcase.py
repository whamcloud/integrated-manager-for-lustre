import inspect
import logging
import paramiko
import re
import time

from django.utils.unittest import TestCase

from testconfig import config

from tests.integration.core.constants import TEST_TIMEOUT

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler('test.log'))


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
    """
    Adds a few non-api specific utility functions for the integration tests.
    """

    def remote_command(self, server, command, expected_return_code=0, timeout=TEST_TIMEOUT):
        """
        Executes a command on a remote server over ssh.

        Sends a command over ssh to a remote machine and returns the stdout,
        stderr, and exit status. It will verify that the exit status of the
        command matches expected_return_code unless expected_return_code=None.
        """
        logger.debug("remote_command[%s]: %s" % (server, command))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, **{'username': 'root'})
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(timeout)
        channel.exec_command(command)
        stdout = channel.makefile('rb')
        stderr = channel.makefile_stderr()
        exit_status = channel.recv_exit_status()
        logger.debug("Remote command exited with status %s." % exit_status)
        if expected_return_code is not None:
            self.assertEqual(exit_status, expected_return_code, stderr.read())
        return RemoteCommandResult(exit_status, stdout, stderr)

    def wait_until_true(self, lambda_expression, timeout=TEST_TIMEOUT):
        """
        Evaluates lambda_expression once/1s until True or hits timeout.
        """
        running_time = 0
        lambda_result = None
        while not lambda_result and running_time < timeout:
            lambda_result = lambda_expression()
            logger.debug("%s evaluated to %s" % (inspect.getsource(lambda_expression), lambda_result))
            time.sleep(1)
            running_time += 1
        self.assertLess(running_time, timeout, "Timed out waiting for %s." % inspect.getsource(lambda_expression))

    def mount_filesystem(self, client, filesystem_name, mount_command, expected_return_code=0):
        """
        Mounts a lustre filesystem on a specified client.
        """
        self.remote_command(
            client,
            "mkdir -p /mnt/%s" % filesystem_name,
            expected_return_code = None  # May fail if already exists. Keep going.
        )

        self.remote_command(
            client,
            mount_command
        )

        result = self.remote_command(
            client,
            'mount'
        )
        self.assertRegexpMatches(
            result.stdout.read(),
            " on /mnt/%s " % filesystem_name
        )

    def unmount_filesystem(self, client, filesystem_name):
        """
        Unmounts a lustre filesystem from the specified client if mounted.
        """
        result = self.remote_command(
            client,
            'mount'
        )
        if re.search(" on /mnt/%s " % filesystem_name, result.stdout.read()):
            logger.debug("Unmounting %s" % filesystem_name)
            self.remote_command(
                client,
                "umount /mnt/%s" % filesystem_name
            )
        result = self.remote_command(
            client,
            'mount'
        )
        mount_output = result.stdout.read()
        logger.debug("`Mount`: %s" % mount_output)
        self.assertNotRegexpMatches(
            mount_output,
            " on /mtn/%s " % filesystem_name
        )

    def get_host_config(self, nodename):
        """
        Get the entry for a lustre server from the cluster config.
        """
        for host in config['lustre_servers']:
            if host['nodename'] == nodename:
                return host

    def get_available_lustre_server(self):
        for host in config['lustre_servers']:
            try:
                self.remote_command(
                    host['address'],
                    'echo "ping!"'
                )
            except Exception:
                continue
            return host
