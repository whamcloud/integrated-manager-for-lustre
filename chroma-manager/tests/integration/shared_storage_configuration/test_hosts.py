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
    def test_alert_long_polling(self):
        """Test long polling for alerts responds correctly."""

        # Add one host
        host = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        # Now start monitoring the endpoint
        long_polling_end_point = LongPollingThread("/api/host/", self)

        self._fetch_help(lambda: self.wait_until_true(lambda: long_polling_end_point.response_count == 1),
                         ['chris.gearing@intel.com'],
                         lambda: "Long polling failed response count == %d" % long_polling_end_point.response_count)

        # Now wait 10 seconds and the the response count should not have changed.
        time.sleep(10)

        self._fetch_help(lambda: self.wait_until_true(lambda: long_polling_end_point.response_count == 1),
                         ['chris.gearing@intel.com'],
                         lambda: "Long polling failed response count == %d" % long_polling_end_point.response_count)

        # Stop LNet and the response should change.
        self.remote_operations.stop_lnet(host['fqdn'])

        # We get two writes to the table, should be optimized for 1 I guess but that is another story.
        self._fetch_help(lambda: self.wait_until_true(lambda: long_polling_end_point.response_count == 3),
                         ['chris.gearing@intel.com'],
                         lambda: "Long polling failed response count == %d" % long_polling_end_point.response_count)

        # Now exit.
        long_polling_end_point.exit = True

        # Need to cause an alert of some sort, or wait for a timeout of long polling, so start Lnet again.
        self.remote_operations.start_lnet(host['fqdn'])
        self._fetch_help(lambda: self.wait_until_true(lambda: long_polling_end_point.response_count == 4),
                         ['chris.gearing@intel.com'],
                         lambda: "Long polling failed response count == %d" % long_polling_end_point.response_count)

        long_polling_end_point.join()

        self.assertEqual(long_polling_end_point.error, None, long_polling_end_point.error)
