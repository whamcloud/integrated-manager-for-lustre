import subprocess
import time

from django.utils.unittest import TestCase

from testconfig import config

from tests.utils.http_requests import HttpRequests
from tests.integration.core.constants import TEST_TIMEOUT


class ChromaIntegrationTestCase(TestCase):

    def reset_cluster(self):
        for hydra_server_config in config['hydra_servers']:
            hydra_server = HttpRequests(
                server_http_url = hydra_server_config['server_http_url'])

            # Unmount and remove filesystems
            response = hydra_server.get(
                '/api/filesystem/'
            )
            filesystems = response.json

            if len(filesystems) > 0:
                remove_filesystem_command_ids = []
                for filesystem in filesystems:
                    # TODO: Adjust to do for every client in the cluster, not
                    # just the one running the tests.
                    process = subprocess.Popen(
                        'umount /mnt/%s' % filesystem['fsname'],
                        shell=True,
                    )
                    process.communicate()

                    response = hydra_server.post(
                        '/api/transition/',
                        data = {
                            'id': filesystem['fsid'],
                            'content_type_id': filesystem['content_type_id'],
                            'new_state': 'removed',
                        }
                    )
                    command_id = response.json['id']
                    self.assertTrue(command_id)
                    remove_filesystem_command_ids.append(command_id)

                self.wait_for_commands(hydra_server, remove_filesystem_command_ids)

            # Verify there are now zero filesystems
            response = hydra_server.get(
                '/api/filesystem/'
            )
            filesystems = response.json
            self.assertEqual(0, len(filesystems))

            # Remove MGT
            response = hydra_server.get(
                '/api/target/',
                params = {'kind': 'MGT'}
            )
            mgts = response.json

            if len(mgts) > 0:
                remove_mgt_command_ids = []
                for mgt in mgts:
                    response = hydra_server.post(
                        '/api/transition/',
                        data = {
                            'id': mgt['id'],
                            'content_type_id': mgt['content_type_id'],
                            'new_state': 'removed',
                        }
                    )
                    command_id = response.json['id']
                    self.assertTrue(command_id)
                    remove_mgt_command_ids.append(command_id)

                self.wait_for_commands(hydra_server, remove_mgt_command_ids)

            # Verify there are now zero mgts
            response = hydra_server.get(
                '/api/target/',
                params = {'kind': 'MGT'}
            )
            mgts = response.json
            self.assertEqual(0, len(mgts))

            # Remove hosts
            response = hydra_server.get(
                '/api/host/',
            )
            self.assertTrue(response.successful, response.text)
            hosts = response.json

            if len(hosts) > 0:
                remove_host_command_ids = []
                for host in hosts:
                    response = hydra_server.post(
                        '/api/transition/',
                        data = {
                            'id': host['id'],
                            'content_type_id': host['content_type_id'],
                            'new_state': 'removed',
                        }
                    )
                    self.assertTrue(response.successful, response.text)
                    command_id = response.json['id']
                    self.assertTrue(command_id)
                    remove_host_command_ids.append(command_id)

                self.wait_for_commands(hydra_server, remove_host_command_ids)

            # Verify there are now zero hosts in the database.
            response = hydra_server.get(
                '/api/host/',
            )
            self.assertTrue(response.successful, response.text)
            hosts = response.json
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
