import subprocess
import time

from django.utils.unittest import TestCase

from tests.integration.core.constants import TEST_TIMEOUT


class ChromaIntegrationTestCase(TestCase):

    def reset_cluster(self, hydra_server):
        # Unmount and remove filesystems
        response = hydra_server.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        filesystems = response.json['objects']

        if len(filesystems) > 0:
            remove_filesystem_command_ids = []
            for filesystem in filesystems:
                # TODO: Adjust to do for every client in the cluster, not
                # just the one running the tests.
                process = subprocess.Popen(
                    'umount /mnt/%s' % filesystem['name'],
                    shell=True,
                )
                process.communicate()

                response = hydra_server.delete(filesystem['resource_uri'])
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
