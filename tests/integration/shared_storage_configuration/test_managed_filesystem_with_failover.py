import json
import subprocess
import time

from testconfig import config

from tests.utils.http_requests import HttpRequests
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.testcases import ChromaIntegrationTestCase


class TestManagedFilesystemWithFailover(ChromaIntegrationTestCase):

    def setUp(self):
        self.hydra_server = HttpRequests(server_http_url =
            config['hydra_servers'][0]['server_http_url'])

    def tearDown(self):
        self.reset_cluster()

    def test_create_filesystem_with_failover(self):
        # Add two hosts as managed hosts
        for host_address in config['lustre_servers'].keys()[:2]:
            response = self.hydra_server.get(
                '/api/test_host/',
                params = {'hostname': host_address}
            )
            self.assertTrue(response.successful, response.text)

            response = self.hydra_server.post(
                '/api/host/',
                data = {'host_name': host_address}
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
        hosts = response.json
        self.assertEqual(2, len(hosts))

        # Wait and verify host configuration and lnet start
        running_time = 0
        servers_configured = False
        while running_time < TEST_TIMEOUT and not servers_configured:
            response = self.hydra_server.post(
                '/api/object_summary/',
                headers = {'content-type': 'application/json'},
                data = json.dumps({'objects': hosts})
            )
            self.assertTrue(response.successful, response.text)
            if response.json[0]['state'] == 'lnet_up' and \
               response.json[1]['state'] == 'lnet_up':
                servers_configured = True
            time.sleep(1)
            running_time += 1

        # Wait for device discovery
        running_time = 0
        usable_luns = []
        while running_time < TEST_TIMEOUT and len(usable_luns) < 4:
            response = self.hydra_server.get(
                '/api/volume/',
                data = {'category': 'usable'}
            )
            self.assertTrue(response.successful, response.text)
            usable_luns = response.json
            time.sleep(1)
            running_time += 1

        # Assert meets the minimum number of devices needed for this test.
        self.assertGreaterEqual(len(usable_luns), 4)

        # Verify no extra devices not in the config visible.
        response = self.hydra_server.get(
            '/api/lun_node/'
        )
        self.assertTrue(response.successful, response.text)
        lun_nodes = response.json

        response = self.hydra_server.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json

        host_id_to_address = dict((h['id'], h['address']) for h in hosts)
        usable_luns_ids = [l['id'] for l in usable_luns]

        for lun_node in lun_nodes:
            if lun_node['lun_id'] in usable_luns_ids:

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
            headers = {'content-type': 'application/json'},
            data = json.dumps({
                'fsname': 'testfs',
                'mgt_id': '',
                'mgt_lun_id': usable_luns[0]['id'],
                'mdt_lun_id': usable_luns[1]['id'],
                'ost_lun_ids': [str(usable_luns[2]['id']), str(usable_luns[3]['id'])],
                'conf_params': '',
            })
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
        mgs_hostname = response.json['mgs_hostname']

        process = subprocess.call(
            'mkdir -p /mnt/testfs',
            shell=True
        )

        process = subprocess.Popen(
            "mount -t lustre %s:/testfs /mnt/testfs" % mgs_hostname,
            shell=True,
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
