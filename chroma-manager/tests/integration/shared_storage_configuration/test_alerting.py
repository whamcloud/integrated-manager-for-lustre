

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestEvents(ChromaIntegrationTestCase):
    def test_reboot_event(self):
        """Test that when a host is restarted, a single corresponding event is generated"""

        # Add one host
        self.add_hosts([config['lustre_servers'][0]['address']])

        # Record the start time for later querying of events since
        # NB using a time from chroma-manager so as not to depend
        # on the test runner's clock
        host = self.get_list("/api/host/")[0]
        start_time = host['state_modified_at']

        # Kill the server
        self.remote_operations.kill_server(host['fqdn'])
        # If STONITH is working, it should arrange for it to come back up
        self.remote_operations.await_server_boot(host['fqdn'])

        def reboot_event_was_seen():
            events = self.get_list("/api/event/", {'created_at__gte': start_time})

            reboot_events = [e for e in events if e['message'].find("restarted") != -1]
            return len(reboot_events) == 1

        self.wait_until_true(reboot_event_was_seen)


class TestAlerting(ChromaIntegrationTestCase):
    def test_alerts(self):
        fs_id = self.create_filesystem_simple()

        fs = self.get_by_uri("/api/filesystem/%s/" % fs_id)
        host = self.get_list("/api/host/")[0]

        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertListEqual(alerts, [])

        mgt = fs['mgt']

        # Check the alert is raised when the target unexpectedly stops
        self.remote_operations.stop_target(host['fqdn'], mgt['ha_label'])
        self.wait_for_assert(lambda: self.assertHasAlert(mgt['resource_uri']))
        self.wait_for_assert(lambda: self.assertState(mgt['resource_uri'], 'unmounted'))

        # Check the alert is cleared when restarting the target
        self.remote_operations.start_target(host['fqdn'], mgt['ha_label'])

        self.wait_for_assert(lambda: self.assertNoAlerts(mgt['resource_uri']))

        # Check that no alert is raised when intentionally stopping the target
        self.set_state(mgt['resource_uri'], 'unmounted')
        self.assertNoAlerts(mgt['resource_uri'])

        # Stop the filesystem so that we can play with the host
        self.set_state(fs['resource_uri'], 'stopped')

        # Check that an alert is raised when lnet unexpectedly goes down
        host = self.get_by_uri(host['resource_uri'])
        self.assertEqual(host['state'], 'lnet_up')
        self.remote_operations.stop_lnet(host['fqdn'])
        self.wait_for_assert(lambda: self.assertHasAlert(host['resource_uri']))
        self.wait_for_assert(lambda: self.assertState(host['resource_uri'], 'lnet_down'))

        # Check that alert is dropped when lnet is brought back up
        self.set_state(host['resource_uri'], 'lnet_up')
        self.assertNoAlerts(host['resource_uri'])

        # Check that no alert is raised when intentionally stopping lnet
        self.set_state(host['resource_uri'], 'lnet_down')
        self.assertNoAlerts(host['resource_uri'])

        # Raise all the alerts we can
        self.set_state("/api/filesystem/%s/" % fs_id, 'available')
        for target in self.get_list("/api/target/"):
            self.remote_operations.stop_target(host['fqdn'], target['ha_label'])
        self.remote_operations.stop_lnet(host['fqdn'])
        self.wait_for_assert(lambda: self.assertEqual(len(self.get_list('/api/alert/', {'active': True})), 4))

        # Remove everything
        self.graceful_teardown(self.chroma_manager)

        # Check that all the alerts are gone too
        self.assertListEqual(self.get_list('/api/alert/', {'active': True}), [])
