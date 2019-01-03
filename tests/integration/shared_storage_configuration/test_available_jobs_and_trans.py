import logging

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase

log = logging.getLogger(__name__)


class TestAvailable(ChromaIntegrationTestCase):
    """Test that the RPC to get available job and transitions works

    This test is mention to verify the RPC and endpoints are all setup and
    working over the process boundaries.  Only a basic state is tested.
    For more detailed coverage of the available_job or available_transition
    method, have a look the the job_control unit tests.
    """

    def test_available_transitions(self):
        """Test that hosts states can be looked up JobScheduler over RPC"""

        server_config_1 = config["lustre_servers"][0]

        # Add two hosts
        self.add_hosts([server_config_1["address"]])

        host1 = self.get_list("/api/host/", args={"fqdn": server_config_1["fqdn"]})[0]

        #  Since no jobs are incomplete (could check it, but na...)
        #  We ought to get some available states, more than 1 at least.
        for trans in host1["available_transitions"]:
            self.assertIn(trans["state"], ["removed"])

    def test_available_jobs(self):
        """Test that hosts job can be looked on the JobScheduler over RPC"""

        def check_expected_jobs(server, expected_jobs):
            host = self.get_list("/api/host/", args={"fqdn": server["fqdn"]})[0]

            returned_jobs = [job["class_name"] for job in host["available_jobs"]]

            self.assertEqual(
                set(returned_jobs),
                set(expected_jobs),
                "Host state %s (%s)\n Host Alerts [%s]"
                % (
                    host["state"],
                    self.get_json_by_uri(host["resource_uri"])["state"],
                    ", ".join(
                        [
                            alert["alert_type"]
                            for alert in self.get_list("/api/alert/", {"active": True, "alert_item_id": host["id"]})
                        ]
                    ),
                ),
            )

        server_config_1 = config["lustre_servers"][0]

        # Add two hosts
        self.add_hosts([server_config_1["address"]])

        #  Since no jobs are incomplete (could check it, but na...)
        #  We ought to get some available states, more than 1 at least.
        self.wait_for_assert(
            lambda: check_expected_jobs(server_config_1, ["ForceRemoveHostJob", "RebootHostJob", "ShutdownHostJob"])
        )

    def test_available_actions(self):
        """Test that hosts actions can be looked on the JobScheduler over RPC

        actions are the union of
          1. jobs (StateChangeJob) used to put an object in an available transitional state, and
          2. jobs (AdvertisedJob) conditionally made available by an obj to be applied to the object.

        Technically these are both just jobs, and 'actions' defines the total list of those jobs.
        """

        server_config_1 = config["lustre_servers"][0]

        host = self.add_hosts([server_config_1["address"]])[0]

        self.set_state(host["lnet_configuration"], "lnet_up")

        lnet_configuration = self.get_by_uri(host["lnet_configuration"]).json
        self.assertEqual(lnet_configuration["state"], "lnet_up")

        returned_job_verbs = [job["verb"] for job in lnet_configuration["available_actions"]]
        expected_verbs_in_order = ["Stop LNet", "Unload LNet"]
        self.assertEqual(returned_job_verbs, expected_verbs_in_order)
