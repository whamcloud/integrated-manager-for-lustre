import paramiko
import re
import time

from django.utils.unittest import TestCase

from testconfig import config

from tests.integration.core.constants import TEST_TIMEOUT


class ChromaIntegrationTestCase(TestCase):

    def reset_cluster(self, hydra_server):
        response = hydra_server.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        filesystems = response.json['objects']

        if len(filesystems) > 0:
            # Unmount filesystems
            for client in config['lustre_clients'].keys():
                for filesystem in filesystems:
                    self.unmount_filesystem(client, filesystem['name'])

            # Remove filesystems
            remove_filesystem_command_ids = []
            for filesystem in filesystems:
                response = hydra_server.delete(filesystem['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_filesystem_command_ids.append(command_id)

            self.wait_for_commands(hydra_server, remove_filesystem_command_ids)

        # Verify there are now zero filesystems
        response = hydra_server.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        filesystems = response.json['objects']
        self.assertEqual(0, len(filesystems))

        # Remove MGT
        response = hydra_server.get(
            '/api/target/',
            params = {'kind': 'MGT', 'limit': 0}
        )
        mgts = response.json['objects']

        if len(mgts) > 0:
            remove_mgt_command_ids = []
            for mgt in mgts:
                response = hydra_server.delete(mgt['resource_uri'])
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_mgt_command_ids.append(command_id)

            self.wait_for_commands(hydra_server, remove_mgt_command_ids)

        # Verify there are now zero mgts
        response = hydra_server.get(
            '/api/target/',
            params = {'kind': 'MGT'}
        )
        mgts = response.json['objects']
        self.assertEqual(0, len(mgts))

        # Remove hosts
        response = hydra_server.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                response = hydra_server.delete(host['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_host_command_ids.append(command_id)

            self.wait_for_commands(hydra_server, remove_host_command_ids)

        # Verify there are now zero hosts in the database.
        response = hydra_server.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']
        self.assertEqual(0, len(hosts))

    def wait_for_command(self, hydra_server, command_id, timeout=TEST_TIMEOUT, verify_successful=True):
        # TODO: More elegant timeout?
        running_time = 0
        command_complete = False
        while running_time < timeout and not command_complete:
            response = hydra_server.get(
                '/api/command/%s/' % command_id,
            )
            self.assertTrue(response.successful, response.text)
            command = response.json
            command_complete = command['complete']
            if not command_complete:
                time.sleep(1)
                running_time += 1

        self.assertTrue(command_complete, command)
        if verify_successful:
            self.assertFalse(command['errored'] or command['cancelled'], command)

    def wait_for_commands(self, hydra_server, command_ids, timeout=TEST_TIMEOUT):
        for command_id in command_ids:
            self.wait_for_command(hydra_server, command_id, timeout)

    def execute_command_on_client(self, client, command, expected_return_code=0):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(client)
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(TEST_TIMEOUT)
        channel.exec_command(command)
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        stderr = channel.makefile_stderr()
        if expected_return_code is not None:
            exit_status = channel.recv_exit_status()
            self.assertEqual(exit_status, expected_return_code, stderr.read())
        return stdin, stdout, stderr

    def mount_filesystem(self, client, filesystem_name, mount_command, expected_return_code=0):
        self.execute_command_on_client(
            client,
            "mkdir -p /mnt/%s" % filesystem_name,
            expected_return_code = None  # May fail if already exists. Keep going.
        )

        self.execute_command_on_client(
            client,
            mount_command
        )

        stdin, stdout, stderr = self.execute_command_on_client(
            client,
            'mount'
        )
        self.assertRegexpMatches(stdout.read(), filesystem_name)

    def unmount_filesystem(self, client, filesystem_name):
        stdin, stdout, stderr = self.execute_command_on_client(
            client,
            'mount'
        )
        if re.search(" on /mnt/%s " % filesystem_name, stdout.read()):
            self.execute_command_on_client(
                client,
                "umount /mnt/%s" % filesystem_name,
            )
            stdin, stdout, stderr = self.execute_command_on_client(
                client,
                'mount'
            )
            self.assertNotRegexpMatches(stdout.read(), filesystem_name)
        else:
            print "Unmount requested for %s, but %s not mounted." % (
                filesystem_name, filesystem_name)

    def exercise_filesystem(self, client, filesystem_name):
        # TODO: Expand on this. Perhaps use existing lustre client tests.
        self.execute_command_on_client(
            client,
            "dd if=/dev/zero of=/mnt/%s/test.dat bs=1K count=500K" % filesystem_name
        )
