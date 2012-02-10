<<<<<<< HEAD
import subprocess
=======
import json
>>>>>>> HYD-596, HYD-597 - Separate clients from test runner, shared fns for system calls.
import time

from testconfig import config

from tests.utils.http_requests import AuthorizedHttpRequests
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.testcases import ChromaIntegrationTestCase


class TestManagedFilesystemWithFailover(ChromaIntegrationTestCase):
    def setUp(self):
        user = config['hydra_servers'][0]['users'][0]
        self.hydra_server = AuthorizedHttpRequests(user['username'], user['password'],
                server_http_url = config['hydra_servers'][0]['server_http_url'])
        self.reset_cluster(self.hydra_server)

    def test_create_filesystem_with_failover(self):
        # Add two hosts as managed hosts
        for host_address in config['lustre_servers'].keys()[:2]:
            response = self.hydra_server.post(
                '/api/test_host/',
                body = {'address': host_address}
            )
            self.assertTrue(response.successful, response.text)
            # FIXME: test_host here isn't serving a purpose as we
            # don't check on its result (it's asynchronous but
            # annoyingly returns a celery task instead of a Command)

            response = self.hydra_server.post(
                '/api/host/',
                body = {'address': host_address}
            )
            self.assertTrue(response.successful, response.text)
            host_id = response.json['id']
            self.assertTrue(host_id)

            response = self.hydra_server.get(
                '/api/host/%s/' % host_id,
            )
            self.assertTrue(response.successful, response.text)
            host = response.json
            self.assertEqual(host['address'], host_address)

        # Verify there are now two hosts in the database.
        response = self.hydra_server.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']
        self.assertEqual(2, len(hosts))

        # Wait and verify host configuration and lnet start
        running_time = 0
        servers_configured = False
        while running_time < TEST_TIMEOUT and not servers_configured:
            if (hosts[0]['state'] == 'lnet_up' and hosts[1]['state'] == 'lnet_up'):
                servers_configured = True
                break

            for h in hosts:
                if h['state'] != 'lnet_up':
                    response = self.hydra_server.get('/api/host/' + h['id'] + "/")
                    self.assertTrue(response.successful, response.text)
                    h['state'] = response.json['state']

            time.sleep(1)
            running_time += 1

        if not servers_configured:
            raise RuntimeError('Timed out setting up hosts')

        # Wait for device discovery
        running_time = 0
        usable_luns = []
        ready_lun_count = 0
        while running_time < TEST_TIMEOUT and ready_lun_count < 4:
            response = self.hydra_server.get(
                '/api/volume/',
                params = {'category': 'usable'}
            )
            self.assertTrue(response.successful, response.text)
            usable_luns = response.json['objects']

            # FIXME: currently depending on settings.PRIMARY_LUN_HACK to
            # set primary and secondary for us.
            #  -> we could readily wait until the volume has two nodes, and then
            #     use the API to set the primary and secondary from the test
            # Count how many of the reported Luns are ready for our test
            # (i.e. they have both a primary and a secondary node)
            ready_lun_count = 0
            for l in usable_luns:
                has_primary = len([node for node in l['volume_nodes'] if node['primary']]) == 1
                has_two = len([node for node in l['volume_nodes'] if node['use']]) >= 2
                if has_primary and has_two:
                    ready_lun_count += 1

            time.sleep(1)
            running_time += 1

        # Assert meets the minimum number of devices needed for this test.
        self.assertGreaterEqual(len(usable_luns), 4)

        # Verify no extra devices not in the config visible.
        response = self.hydra_server.get(
            '/api/volume_node/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        lun_nodes = response.json['objects']

        response = self.hydra_server.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        host_id_to_address = dict((h['id'], h['address']) for h in hosts)
        usable_luns_ids = [l['id'] for l in usable_luns]

        for lun_node in lun_nodes:
            if lun_node['volume_id'] in usable_luns_ids:

                # Create a list of usable device paths for the host of the
                # current lun node as listed in the config.
                host_id = lun_node['host_id']
                host_address = host_id_to_address[host_id]
                config_device_paths = config['lustre_servers'][host_address]['device_paths']
                config_paths = [str(p) for p in config_device_paths]

                self.assertTrue(lun_node['path'] in config_paths,
                    "Path: %s Config Paths: %s" % (
                        lun_node['path'], config_device_paths)
                )

        # Create new filesystem
        response = self.hydra_server.post(
            '/api/filesystem/',
            body = {
                'name': 'testfs',
                'mgt_id': '',
                'mgt_lun_id': usable_luns[0]['id'],
                'mdt_lun_id': usable_luns[1]['id'],
                'ost_lun_ids': [str(usable_luns[2]['id']), str(usable_luns[3]['id'])],
                'conf_params': {},
            }
        )
        self.assertTrue(response.successful, response.text)
        command_id = response.json['command']['id']
        filesystem_id = response.json['filesystem']['id']

        # Wait for filesystem setup
        self.wait_for_command(self.hydra_server, command_id)

        # Mount the filesystem
        response = self.hydra_server.get(
            '/api/filesystem/%s/' % filesystem_id,
        )
        self.assertTrue(response.successful, response.text)
        mount_command = response.json['mount_command']

<<<<<<< HEAD
        process = subprocess.call(
            'mkdir -p /mnt/testfs',
            shell=True
        )

        process = subprocess.Popen(
            mount_command,
            shell=True
        )
        process.communicate()
        self.assertEqual(0, process.returncode)

        # TODO: Probably replace this with just writing a file in Python.
        process = subprocess.Popen(
            'dd if=/dev/zero of=/mnt/testfs/test.dat bs=1K count=500K',
            shell=True,
        )
        process.communicate()
        self.assertEqual(0, process.returncode)

        # TODO: Verify file now on testfs filesystem. Possibly reuse
        # some existing Lustre tests here to exercise the fs?
=======
        client = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client, "testfs", mgs_hostname)
        self.exercise_filesystem(client, "testfs")
>>>>>>> HYD-596, HYD-597 - Separate clients from test runner, shared fns for system calls.
