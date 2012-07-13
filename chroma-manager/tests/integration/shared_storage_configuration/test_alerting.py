
from testconfig import config
import time
from tests.integration.core.testcases import ChromaIntegrationTestCase
from tests.utils.http_requests import AuthorizedHttpRequests


class TestAlerting(ChromaIntegrationTestCase):
    def setUp(self):
        self.reset_cluster()
        user = config['chroma_managers'][0]['users'][0]
        self.chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
            server_http_url = config['chroma_managers'][0]['server_http_url'])

    def test_alerts(self):
        fs_id = self.create_filesystem_simple()

        #self.set_state("/api/filesystem/%s/" % fs_id, 'available')
        fs = self.get_by_uri("/api/filesystem/%s/" % fs_id)
        host = self.get_list("/api/host/")[0]

        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertListEqual(alerts, [])

        mgt = fs['mgt']

        # Check the alert is raised when the target unexpectedly stops
        self.remote_command(host['address'], "chroma-agent stop-target --ha_label %s" % mgt['ha_label'])
        # Updating the status is a (very) asynchronous operation
        # 10 second periodic update from the agent, then the state change goes
        # into a queue serviced at some time by the serialize worker.
        time.sleep(20)
        self.assertHasAlert(mgt['resource_uri'])
        self.assertState(mgt['resource_uri'], 'unmounted')

        # Check the alert is cleared when restarting the target
        self.remote_command(host['address'], "chroma-agent start-target --ha_label %s" % mgt['ha_label'])
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
            self.remote_command(host['address'], "chroma-agent stop-target --ha_label %s" % target['ha_label'])
        self.remote_command(host['address'], "chroma-agent stop-lnet")
        time.sleep(20)
        self.assertEqual(len(self.get_list('/api/alert', {'active': True})), 4)

        # Remove everything
        self.graceful_teardown(self.chroma_manager)

        # Check that all the alerts are gone too
        self.assertListEqual(self.get_list('/api/alert/', {'active': True}), [])
