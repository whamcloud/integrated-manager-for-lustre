
from testconfig import config

from tests.utils.http_requests import AuthorizedHttpRequests
from tests.integration.core.testcases import ChromaIntegrationTestCase


class TestManagedFilesystemWithFailover(ChromaIntegrationTestCase):
    def setUp(self):
        user = config['hydra_servers'][0]['users'][0]
        self.hydra_server = AuthorizedHttpRequests(user['username'], user['password'],
                server_http_url = config['hydra_servers'][0]['server_http_url'])
        self.reset_cluster(self.hydra_server)

    def test_create_filesystem_with_failover(self):
        # Add two hosts as managed hosts
        host_create_command_ids = []
        for host_config in config['lustre_servers'][:2]:
            host_address = host_config['address']
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
            print response.json
            host_id = response.json['host']['id']
            host_create_command_ids.append(response.json['command']['id'])
            self.assertTrue(host_id)

            response = self.hydra_server.get(
                '/api/host/%s/' % host_id,
            )
            self.assertTrue(response.successful, response.text)
            host = response.json
            self.assertEqual(host['address'], host_address)

        # Wait for the host setup and device discovery to complete
        self.wait_for_commands(self.hydra_server, host_create_command_ids)

        # Verify there are now two hosts in the database.
        response = self.hydra_server.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']
        self.assertEqual(2, len(hosts))
        self.assertEqual(hosts[0]['state'], 'lnet_up')
        self.assertEqual(hosts[1]['state'], 'lnet_up')

        # Wait for device discovery
        ha_luns = []
        response = self.hydra_server.get(
            '/api/volume/',
            params = {'category': 'usable'}
        )
        self.assertTrue(response.successful, response.text)

        # FIXME: currently depending on settings.PRIMARY_LUN_HACK to
        # set primary and secondary for us.
        #  -> we could readily wait until the volume has two nodes, and then
        #     use the API to set the primary and secondary from the test
        # Count how many of the reported Luns are ready for our test
        # (i.e. they have both a primary and a secondary node)
        ha_luns = []
        for l in response.json['objects']:
            has_primary = len([node for node in l['volume_nodes'] if node['primary']]) == 1
            has_two = len([node for node in l['volume_nodes'] if node['use']]) >= 2
            if has_primary and has_two:
                ha_luns.append(l)
        self.assertGreaterEqual(len(ha_luns), 4)

        # Create new filesystem
        self.verify_usable_luns_valid(ha_luns, 4)
        filesystem_id = self.create_filesystem(
            name = 'testfs',
            mgt_lun_id = ha_luns[0]['id'],
            mdt_lun_id = ha_luns[1]['id'],
            ost_lun_ids = [str(ha_luns[2]['id']), str(ha_luns[3]['id'])]
        )

        # Mount the filesystem
        response = self.hydra_server.get(
            '/api/filesystem/%s/' % filesystem_id,
        )
        self.assertTrue(response.successful, response.text)
        mount_command = response.json['mount_command']

        client = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client, "testfs", mount_command)
        self.exercise_filesystem(client, "testfs")
