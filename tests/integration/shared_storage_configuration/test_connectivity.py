import time
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from django.utils.unittest import skip
from testconfig import config


HTTP_POLL_PERIOD = 30
LOST_CONTACT_TIMEOUT = HTTP_POLL_PERIOD
HOST_POLL_PERIOD = 10
MAX_AGENT_BACKOFF = 60


@skip("Needs setup on real hardware")
class TestConnectivity(ChromaIntegrationTestCase):
    """
    Tests for the agent-manager communications behaviour when subject to communications failures.

    There different types of failure:
     * Agent cannot cannot connect to manager
     * An HTTP response is dropped after being composed by the manager
     * A connection is not closed promptly by the manager (e.g. it's dropped with no FIN)
     * A connection is not closed promptly by the agent (e.g. it's dropped with no FIN)
    """

    def _test_failure(self, start_failure_cb, end_failure_cb, time_to_failure):
        """
        Test that under some failure condition in the communications:
         * Alerts are raised
         * After recovery, both monitoring and actions are working
        """
        host = self.add_hosts([self.TEST_SERVERS[0]["address"]])[0]

        # Initially running a command should work
        self.set_state(host["lnet_configuration"], "lnet_up")
        self.set_state(host["lnet_configuration"], "lnet_down")

        # Initially there should be one WARNING alert because our host has no corosync peer.
        self.wait_alerts(["CorosyncNoPeersAlert"], active=True, severity="WARNING")

        active_lost_contact_filter = {"active": True, "alert_type": "HostContactAlert"}

        # Enter the failure mode
        start_failure_cb()
        try:
            self.wait_until_true(
                lambda: len(self.get_list("/api/alert/", active_lost_contact_filter)) != 0, timeout=time_to_failure
            )  # Long enough to time out and notice timing out

            # A 'Lost contact' alert should be raised
            self.assertHasAlert(host["resource_uri"])
            alerts = self.get_list("/api/alert/", active_lost_contact_filter)
            self.assertEqual(len(alerts), 1)
            self.assertRegexpMatches(alerts[0]["message"], "Lost contact with host.*")

            # Commands should not work
            failed_command = self.set_state(host["lnet_configuration"], "lnet_up", verify_successful=False)
            self.assertTrue(failed_command["errored"], True)
        finally:
            # Leave the failure mode
            end_failure_cb()
            self.remote_operations.fail_connections(False)

        # The alert should go away
        self.wait_until_true(
            lambda: len(self.get_list("/api/alert/", active_lost_contact_filter)) == 0, timeout=MAX_AGENT_BACKOFF * 2
        )  # The agent may have backed off up to its max backoff

        # The alert goes away as soon as an agent GET gets through, but the action_runner session might
        # not be re-established until the max backoff period
        # Because we can't observe whether the action_runner session is active, have to do a 'blind' sleep
        # here rather than a wait_until_true
        time.sleep(MAX_AGENT_BACKOFF)

        # Running a command should work again
        self.set_state(host["lnet_configuration"], "lnet_up")
        self.set_state(host["lnet_configuration"], "lnet_down")

    def test_cannot_connect(self):
        """
        Test that when agent cannot open connections to manager:
         * Alerts are raised
         * After recovery, both monitoring and actions are working
        """
        self._test_failure(
            lambda: self.remote_operations.fail_connections(True),
            lambda: self.remote_operations.fail_connections(False),
            LOST_CONTACT_TIMEOUT * 2 + HOST_POLL_PERIOD,
        )

    def test_responses_dropped(self):

        self._test_failure(
            lambda: self.remote_operations.drop_responses(True),
            lambda: self.remote_operations.drop_responses(False),
            HTTP_POLL_PERIOD + LOST_CONTACT_TIMEOUT * 2 + HOST_POLL_PERIOD,
        )
