
from testconfig import config
import time
from tests.integration.core.testcases import ChromaIntegrationTestCase
from tests.utils.http_requests import AuthorizedHttpRequests


class TestAlerting(ChromaIntegrationTestCase):
    def setUp(self):
        user = config['chroma_managers'][0]['users'][0]
        self.chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
            server_http_url = config['chroma_managers'][0]['server_http_url'])
        self.reset_cluster(self.chroma_manager)

    def create_filesystem_simple(self):
        self.add_hosts([config['lustre_servers'][0]['address']])

        ha_volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(ha_volumes), 4)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volumes = [ha_volumes[2]]
        return self.create_filesystem(
                {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': {}
                },
                'osts': [{
                    'volume_id': v['id'],
                    'conf_params': {}
                } for v in ost_volumes],
                'conf_params': {}
            }
        )

    def get_list(self, url, args = {}):
        response = self.chroma_manager.get(url, params = args)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json['objects']

    def set_state(self, uri, state):
        object = self.get_by_uri(uri)
        object['state'] = state

        response = self.chroma_manager.put(uri, body = object)
        if response.status_code == 204:
            return
        elif response.status_code == 202:
            self.wait_for_command(self.chroma_manager, response.json['command']['id'])
        else:
            self.assertEquals(response.status_code, 202, response.content)

        self.assertState(uri, state)

    def get_by_uri(self, uri):
        response = self.chroma_manager.get(uri)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json

    def assertNoAlerts(self, uri):
        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertNotIn(uri, [a['alert_item'] for a in alerts])

    def assertHasAlert(self, uri):
        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertIn(uri, [a['alert_item'] for a in alerts])

    def assertState(self, uri, state):
        obj = self.get_by_uri(uri)
        self.assertEqual(obj['state'], state)

    def test_alerts(self):
        fs_id = self.create_filesystem_simple()

        #self.set_state("/api/filesystem/%s/" % fs_id, 'available')
        fs = self.get_by_uri("/api/filesystem/%s/" % fs_id)
        host = self.get_list("/api/host/")[0]

        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertListEqual(alerts, [])

        mgt = fs['mgt']

        # Check the alert is raised when the target unexpectedly stops
        self.remote_command(host['address'], "chroma-agent stop-target --label %s --id %s" % (mgt['name'], mgt['id']))
        # Updating the status is a (very) asynchronous operation
        # 10 second periodic update from the agent, then the state change goes
        # into a queue serviced at some time by the serialize worker.
        time.sleep(20)
        self.assertHasAlert(mgt['resource_uri'])
        self.assertState(mgt['resource_uri'], 'unmounted')

        # Check the alert is cleared when restarting the target
        self.remote_command(host['address'], "chroma-agent start-target --label %s --id %s" % (mgt['name'], mgt['id']))
        time.sleep(20)
        self.assertNoAlerts(mgt['resource_uri'])

        # Check that no alert is raised when intentionally stopping the target
        self.set_state(mgt['resource_uri'], 'unmounted')
        self.assertNoAlerts(mgt['resource_uri'])

        # Stop the filesystem so that we can play with the host
        self.set_state(fs['resource_uri'], 'stopped')

        # Check that an alert is raised when lnet unexpectedly goes down
        host = self.get_by_uri(host['resource_uri'])
        self.assertEqual(host['state'], 'lnet_up')
        self.remote_command(host['address'], "chroma-agent stop-lnet")
        time.sleep(20)
        self.assertHasAlert(host['resource_uri'])
        self.assertState(host['resource_uri'], 'lnet_down')

        # Check that alert is dropped when lnet is brought back up
        self.set_state(host['resource_uri'], 'lnet_up')
        self.assertNoAlerts(host['resource_uri'])

        # Check that no alert is raised when intentionally stopping lnet
        self.set_state(host['resource_uri'], 'lnet_down')
        self.assertNoAlerts(host['resource_uri'])

        # Raise all the alerts we can
        self.set_state("/api/filesystem/%s/" % fs_id, 'available')
        for target in self.get_list("/api/target/"):
            self.remote_command(host['address'], "chroma-agent stop-target --label %s --id %s" % (target['name'], target['id']))
        self.remote_command(host['address'], "chroma-agent stop-lnet")
        time.sleep(20)
        self.assertEqual(len(self.get_list('/api/alert', {'active': True})), 4)

        # Remove everything
        self.reset_cluster(self.chroma_manager)

        # Check that all the alerts are gone too
        self.assertListEqual(self.get_list('/api/alert/', {'active': True}), [])
