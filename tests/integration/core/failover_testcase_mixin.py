import logging
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)


class FailoverTestCaseMixin(ChromaIntegrationTestCase):
    """
    This TestCase Mixin adds functionality for failing over/back targets.
    It is meant to be used with ChromaIntegrationTestCase using multiple
    inheritance just for the integration test classes that require
    failover funcitonality.
    """

    def failover(
        self,
        primary_host,
        secondary_host,
        filesystem_id,
        volumes_expected_hosts_in_normal_state,
        volumes_expected_hosts_in_failover_state,
    ):
        """
        Kills the primary host, ensures failover occurs, and failback doesn't.

        This function will use the command provided in the config to kill the
        primary_host. It then verifies that the target properly fails over to
        the secondary_host. It also waits for the destroyed host to come back
        online and checks that targets do not auto-failback. Checks that all
        volumes are running where expected both before and after failover based
        on volumes_expected_hosts_in_*_state. Expects format:
            {
                foo_vol_id: foo_expected_host_dict,
                bar_vol_id: bar_expected_host_dict,
                ...
            }
        """
        # Attach configurations to primary host so we can retreive information
        # about its vmhost and how to destroy it.
        primary_host["config"] = self.get_host_config(primary_host["nodename"])

        # "Push the power off button" on the primary lustre server
        self.remote_operations.kill_server(primary_host["config"]["fqdn"])

        # Wait for failover to occur
        self.wait_until_true(
            lambda: self.targets_for_volumes_started_on_expected_hosts(
                filesystem_id, volumes_expected_hosts_in_failover_state
            )
        )
        self.verify_targets_for_volumes_started_on_expected_hosts(
            filesystem_id, volumes_expected_hosts_in_failover_state
        )

        # Start up the primary now
        self.remote_operations.start_server(primary_host["config"]["fqdn"])
        self.remote_operations.await_server_boot(primary_host["fqdn"], secondary_host["fqdn"])

        # Verify did not auto-failback
        self.wait_until_true(
            lambda: self.targets_for_volumes_started_on_expected_hosts(
                filesystem_id, volumes_expected_hosts_in_failover_state
            )
        )
        self.verify_targets_for_volumes_started_on_expected_hosts(
            filesystem_id, volumes_expected_hosts_in_failover_state
        )

    def chroma_controlled_failover(
        self,
        primary_host,
        secondary_host,
        filesystem_id,
        volumes_expected_hosts_in_normal_state,
        volumes_expected_hosts_in_failover_state,
    ):
        """
        Works like failover(), except that instead of killing the primary host to simulate
        an unexpected loss of a server, this uses chroma to failover a server intentionally.
        (ex use case: someone needs to service the primary server)
        """
        response = self.chroma_manager.get("/api/target/", params={"filesystem_id": filesystem_id})
        self.assertTrue(response.successful, response.text)
        targets_running_on_primary_host = [
            t for t in response.json["objects"] if t["active_host"] == primary_host["resource_uri"]
        ]

        failover_target_command_ids = []
        for target in targets_running_on_primary_host:
            response = self.chroma_manager.post(
                "/api/command/",
                body={
                    "jobs": [{"class_name": "FailoverTargetJob", "args": {"target_id": target["id"]}}],
                    "message": "Failing %s over to secondary" % target["label"],
                },
            )
            self.assertEqual(response.successful, True, response.text)
            command = response.json
            failover_target_command_ids.append(command["id"])

        self.wait_for_commands(self.chroma_manager, failover_target_command_ids)

        # Wait for failover to occur
        self.wait_until_true(
            lambda: self.targets_for_volumes_started_on_expected_hosts(
                filesystem_id, volumes_expected_hosts_in_failover_state
            )
        )
        self.verify_targets_for_volumes_started_on_expected_hosts(
            filesystem_id, volumes_expected_hosts_in_failover_state
        )

        # Verify did not auto-failback
        self.verify_targets_for_volumes_started_on_expected_hosts(
            filesystem_id, volumes_expected_hosts_in_failover_state
        )

    def failback(self, primary_host, filesystem_id, volumes_expected_hosts_in_normal_state):
        """
        Trigger failback for all failed over targets with primary_host as their primary server
        and verifies after that volumes are running back in their expected locations.
        """
        response = self.chroma_manager.get("/api/target/", params={"filesystem_id": filesystem_id})
        self.assertTrue(response.successful, response.text)
        targets_with_matching_primary_host = [
            t for t in response.json["objects"] if t["primary_server"] == primary_host["resource_uri"]
        ]

        failback_target_command_ids = []
        for target in targets_with_matching_primary_host:
            response = self.chroma_manager.post(
                "/api/command/",
                body={
                    "jobs": [{"class_name": "FailbackTargetJob", "args": {"target_id": target["id"]}}],
                    "message": "Failing %s back to primary" % target["label"],
                },
            )
            self.assertEqual(response.successful, True, response.text)
            command = response.json
            failback_target_command_ids.append(command["id"])

        self.wait_for_commands(self.chroma_manager, failback_target_command_ids)

        # Wait for the targets to move back to their original server.
        self.wait_until_true(
            lambda: self.targets_for_volumes_started_on_expected_hosts(
                filesystem_id, volumes_expected_hosts_in_normal_state
            )
        )
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state)

    def targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts):
        """
        Determine if the targets associated with each volume is running on the expected host.

        Use this version of this check if you want test execution to continue
        and just want a boolean to check if it is as expected.
        """
        return self.check_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_to_expected_hosts, False)

    def verify_targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts):
        """
        Assert targets associated with each volume is running on the expected host.

        Use this version of this check if you expect the targets to be on their
        proper hosts already and want test execution to be halted if not.
        """
        return self.check_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_to_expected_hosts, True)
