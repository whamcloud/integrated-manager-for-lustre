

from testconfig import config
from tests.utils import wait
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestEvents(ChromaIntegrationTestCase):
    TEST_SERVERS = [config['lustre_servers'][0]]

    def test_reboot_event(self):
        """Test that when a host is restarted, a single corresponding event is generated"""

        # Add one host
        self.add_hosts([self.TEST_SERVERS[0]['address']])

        # Record the start time for later querying of events since
        # NB using a time from chroma-manager so as not to depend
        # on the test runner's clock
        host = self.get_list("/api/host/")[0]
        start_time = host['state_modified_at']

        # Reboot
        self.remote_operations.reset_server(host['fqdn'])
        self.remote_operations.await_server_boot(host['fqdn'])

        def reboot_event_was_seen():
            events = self.get_list("/api/alert/", {'begin__gte': start_time})

            reboot_events = [e for e in events if e['message'].find("restarted") != -1]
            return len(reboot_events) == 1

        self.wait_until_true(reboot_event_was_seen)


class TestAlerting(ChromaIntegrationTestCase):
    def _wait_alerts(self, expected_alerts, **filters):
        "Wait and assert correct number of matching alerts."
        expected_alerts.sort()

        for index in wait(timeout=TEST_TIMEOUT):
            alerts = [alert['alert_type'] for alert in self.get_list("/api/alert/", filters)]
            alerts.sort()
            if alerts == expected_alerts:
                return alerts
        raise AssertionError(alerts)

    def test_alerts(self):
        fs_id = self.create_filesystem_simple()

        fs = self.get_json_by_uri("/api/filesystem/%s/" % fs_id)
        host = self.get_list("/api/host/")[0]

        self._wait_alerts([], active=True, severity='ERROR')

        mgt = fs['mgt']

        # Check the ERROR alert is raised when the target unexpectedly stops
        result = self.remote_operations.stop_target(host['fqdn'], mgt['ha_label'])
        try:
            self.wait_for_assert(lambda: self.assertHasAlert(mgt['resource_uri'], of_severity='ERROR'))
        except AssertionError:
            if hasattr(result, 'stdout'):
                print result.stdout  # command exit_status was already checked, but display output anyway
            raise
        self.wait_for_assert(lambda: self.assertState(mgt['resource_uri'], 'unmounted'))
        target_offline_alert = self.get_alert(mgt['resource_uri'], alert_type="TargetOfflineAlert")
        self.assertEqual(target_offline_alert['severity'], 'ERROR')
        self.assertEqual(target_offline_alert['alert_type'], 'TargetOfflineAlert')

        # Check the alert is cleared when restarting the target
        self.remote_operations.start_target(host['fqdn'], mgt['ha_label'])

        self.wait_for_assert(lambda: self.assertNoAlerts(mgt['resource_uri']))

        # Check that no alert is raised when intentionally stopping the target
        self.set_state(mgt['resource_uri'], 'unmounted')

        # Expects no alerts?  This code above WILL generate alerts.  It used
        # to generate them in the dismissed state, and this method would ignore
        # dismissed alerts.  The system now never creates dismissed alerts.
        # So, this method instead checks for any alerts with severity ERROR,
        # since the new code that used to create alerts dismissed will
        # now create the alerts in WARNING
        self.assertNoAlerts(mgt['resource_uri'], of_severity='ERROR')

        # Stop the filesystem so that we can play with the host
        self.set_state(fs['resource_uri'], 'stopped')

        # Check that an alert is raised when lnet unexpectedly goes down
        host = self.get_json_by_uri(host['resource_uri'])
        self.assertEqual(host['state'], 'managed')
        self.remote_operations.stop_lnet(host['fqdn'])
        self.wait_for_assert(lambda: self.assertHasAlert(host['lnet_configuration'], of_severity='INFO'))
        self.wait_for_assert(lambda: self.assertState(host['lnet_configuration'], 'lnet_down'))
        lnet_offline_alert = self.get_alert(host['lnet_configuration'], alert_type="LNetOfflineAlert")
        self.assertEqual(lnet_offline_alert['severity'], 'INFO')

        # Check that alert is dropped when lnet is brought back up
        self.set_state(host['lnet_configuration'], 'lnet_up')
        self.assertNoAlerts(host['lnet_configuration'], of_severity='ERROR')

        # Check that no alert is raised when intentionally stopping lnet
        self.set_state(host['lnet_configuration'], 'lnet_down')
        self.assertNoAlerts(host['lnet_configuration'], of_severity='ERROR')

        # Raise all the alerts we can
        self.set_state("/api/filesystem/%s/" % fs_id, 'available')
        for target in self.get_list("/api/target/"):
            self.remote_operations.stop_target(host['fqdn'], target['ha_label'])
        self.remote_operations.stop_lnet(host['fqdn'])
        self.remote_operations.stop_pacemaker(host['fqdn'])
        self.remote_operations.stop_corosync(host['fqdn'])

        self._wait_alerts(['TargetOfflineAlert',
                           'TargetOfflineAlert',
                           'TargetOfflineAlert',
                           'LNetOfflineAlert',
                           'PacemakerStoppedAlert',
                           'CorosyncStoppedAlert'],
                          active=True)

        # Now with Pacemaker/Corosync/LNetDown down the machine is going to have issues and the user would expect
        # to not be able to do things - at least they should expect, so put them back up.
        self.remote_operations.start_lnet(host['fqdn'])
        self.remote_operations.start_corosync(host['fqdn'])
        self.remote_operations.start_pacemaker(host['fqdn'])

        self._wait_alerts(['TargetOfflineAlert',
                           'TargetOfflineAlert',
                           'TargetOfflineAlert'],
                          active=True)

        # Remove everything
        self.graceful_teardown(self.chroma_manager)

        # Check that all the alerts are gone too
        self._wait_alerts([], active=True)
