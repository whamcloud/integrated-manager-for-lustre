import time

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.long_polling_testing import LongPollingThread


class TestHosts(ChromaIntegrationTestCase):
    def test_hosts_add_existing_filesystem(self):
        # Create a file system and then add new hosts/volumes to it
        hosts = self.add_hosts([
            config['lustre_servers'][0]['address'],
            config['lustre_servers'][1]['address']
        ])

        volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(volumes), 3)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volume = volumes[2]
        self.set_volume_mounts(mgt_volume, hosts[0]['id'], hosts[1]['id'])
        self.set_volume_mounts(mdt_volume, hosts[0]['id'], hosts[1]['id'])
        self.set_volume_mounts(ost_volume, hosts[1]['id'], hosts[0]['id'])

        filesystem_id = self.create_filesystem(
            {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdts': [{
                    'volume_id': mdt_volume['id'],
                    'conf_params': {}
                }],
                'osts': [{
                    'volume_id': ost_volume['id'],
                    'conf_params': {}
                }],
                'conf_params': {}
            }
        )
        filesystem_uri = "/api/filesystem/%s/" % filesystem_id

        self.add_hosts([
            config['lustre_servers'][2]['address']
        ])

        new_volumes = [v for v in self.get_usable_volumes() if v not in volumes]
        self.assertGreaterEqual(len(new_volumes), 1)

        # add the new volume to the existing filesystem
        response = self.chroma_manager.post("/api/target/", body = {
            'volume_id': new_volumes[0]['id'],
            'kind': 'OST',
            'filesystem_id': filesystem_id
        })
        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json['target']['resource_uri']
        create_command = response.json['command']['id']
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, 'mounted')
        self.assertState(filesystem_uri, 'available')

        self.assertEqual(len(self.chroma_manager.get("/api/filesystem/").json['objects'][0]['osts']), 2)


class TestHostLongPolling(ChromaIntegrationTestCase):
    def _wait_response_count(self, count):
        self.wait_until_true(lambda: self.long_polling_end_point.response_count == count,
                             error_message=lambda: ('Expected count {0}\n'
                                                    'Actual Count {1}\n'
                                                    'Polling Data {2}').format(count,
                                                                              self.long_polling_end_point.response_count,
                                                                              self.long_polling_end_point))

    def test_host_long_polling(self):
        """Test long polling for alerts responds correctly."""

        # Add one host
        host = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        # Now start monitoring the endpoint
        self.long_polling_end_point = LongPollingThread("/api/host/", self)

        self._wait_response_count(1)

        # Now wait 10 seconds and the the response count should not have changed.
        time.sleep(10)

        self._wait_response_count(1)

        # Stop LNet and the response should change.
        self.remote_operations.stop_lnet(host['fqdn'])

        self._wait_response_count(2)

        # Now exit.
        self.long_polling_end_point.exit = True

        # Need to cause an alert of some sort, or wait for a timeout of long polling, so start Lnet again.
        self.remote_operations.start_lnet(host['fqdn'])
        self._wait_response_count(3)

        self.long_polling_end_point.join()

        self.assertEqual(self.long_polling_end_point.error, None, self.long_polling_end_point.error)
