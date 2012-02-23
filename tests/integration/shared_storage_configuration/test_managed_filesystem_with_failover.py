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

        # Create new filesystem
        self.verify_usable_luns_valid(usable_luns, 4)
        filesystem_id = self.create_filesystem(
            name = 'testfs',
            mgt_lun_id = usable_luns[0]['id'],
            mdt_lun_id = usable_luns[1]['id'],
            ost_lun_ids = [str(usable_luns[2]['id']), str(usable_luns[3]['id'])]
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
