from testconfig import config
from django.utils.unittest import skip
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


@skip("Needs setup on real hardware")
class TestCommandAlert(ChromaIntegrationTestCase):
    def _check_alert(self, alert_item_id, uri, alert_type):
        all_alerts = self.get_list(
            "/api/alert/",
            {
                "alert_item_id": alert_item_id,
                "alert_type__in": [
                    "CommandSuccessfulAlert",
                    "CommandCancelledAlert",
                    "CommandRunningAlert",
                    "CommandErroredAlert",
                ],
            },
        )

        alerts = [a for a in all_alerts if a["alert_item"] == uri]
        self.assertEqual(len(alerts), 1, "Multiple alerts match: %s" % alerts)
        self.assertEqual(alerts[0]["alert_type"], alert_type)

    def test_successful_alert(self):
        """Test that a CommandSuccessful Alert is returned when changing the Lnet State(Up or Down)"""

        # Add one host
        self.add_hosts([self.TEST_SERVERS[0]["address"]])

        # Get list of hosts
        host = self.get_list("/api/host/")[0]

        # Get dictionary then change lnet state
        lnet_configuration_uri = host["lnet_configuration"]
        lnet_command = self.get_json_by_uri(lnet_configuration_uri)
        lnet_command["state"] = "lnet_down" if lnet_command["state"] == "lnet_up" else "lnet_up"
        response = self.chroma_manager.put(lnet_configuration_uri, body=lnet_command)
        resource_uri = response.json["command"]["resource_uri"]

        # Wait for the command to succeed
        self.wait_for_command(
            self.chroma_manager,
            response.json["command"]["id"],
            verify_successful=False,
            test_for_eventual_completion=False,
        )

        # Check There Is A CommandSuccessfulAlert After Completetion of Job
        self._check_alert(response.json["command"]["id"], resource_uri, "CommandSuccessfulAlert")

    def test_error_alert(self):
        """Test that a CommandError Alert is returned when changing the Lnet State(Up or Down)"""

        # Add one host
        self.add_hosts([self.TEST_SERVERS[0]["address"]])

        # Get list of hosts
        host = self.get_list("/api/host/")[0]

        # Get dictionary then change lnet state
        lnet_configuration_uri = host["lnet_configuration"]

        # Stop Agent
        # self.remote_operations.stop_agent(host['fqdn'])
        self.remote_operations.fail_connections(True)

        lnet_command = self.get_json_by_uri(lnet_configuration_uri)
        lnet_command["state"] = "lnet_down" if lnet_command["state"] == "lnet_up" else "lnet_up"
        response = self.chroma_manager.put(lnet_configuration_uri, body=lnet_command)
        resource_uri = response.json["command"]["resource_uri"]

        # Wait for the command to finish
        self.wait_for_command(
            self.chroma_manager,
            response.json["command"]["id"],
            verify_successful=False,
            test_for_eventual_completion=False,
        )

        # Check There Is A CommandErrorAlert After Unsuccessful Job
        self._check_alert(response.json["command"]["id"], resource_uri, "CommandErroredAlert")
        self.remote_operations.fail_connections(False)

        # Start Agent
        # self.remote_operations.start_agent(host['fqdn'])

    def test_cancel_alert(self):
        """Test that a CommandCancel Alert is returned when changing the Lnet State(Up or Down)"""

        # Add one host
        self.add_hosts([self.TEST_SERVERS[0]["address"]])

        # Get list of hosts
        host = self.get_list("/api/host/")[0]

        # Get dictionary then change lnet state
        lnet_configuration_uri = host["lnet_configuration"]
        lnet_command = self.get_json_by_uri(lnet_configuration_uri)
        lnet_command["state"] = "lnet_down" if lnet_command["state"] == "lnet_up" else "lnet_up"
        response = self.chroma_manager.put(lnet_configuration_uri, body=lnet_command)
        resource_uri = response.json["command"]["resource_uri"]
        self.remote_operations.fail_connections(True)

        job_command = self.get_json_by_uri(resource_uri)
        job_resource_uri = job_command["jobs"][0]
        job = self.get_json_by_uri(job_command["jobs"][0])

        # Check There Is A CommandRunningAlert Before Cancelling The Job
        self._check_alert(response.json["command"]["id"], resource_uri, "CommandRunningAlert")

        # change job state from 'tasked' to cancel
        job["state"] = "cancelled"
        self.remote_operations.fail_connections(False)
        self.chroma_manager.put(job_resource_uri, body=job)

        # Check There Is A CommandCancelAlert After Cancelling The Job
        self._check_alert(response.json["command"]["id"], resource_uri, "CommandCancelledAlert")
