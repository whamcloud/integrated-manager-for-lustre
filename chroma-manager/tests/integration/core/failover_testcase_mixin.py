import logging
import re
import socket
import time

from tests.integration.core.api_testcase import ApiTestCase
from tests.integration.core.constants import TEST_TIMEOUT

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class FailoverTestCaseMixin(ApiTestCase):
    """
    This TestCase Mixin adds functionality for failing over/back targets.
    It is meant to be used with ChromaIntegrationTestCase using multiple
    inheritance just for the integration test classes that require
    failover funcitonality.
    """

    def failover(self, primary_host, secondary_host, filesystem_id, volumes_expected_hosts_in_normal_state, volumes_expected_hosts_in_failover_state):
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
        primary_host['config'] = self.get_host_config(primary_host['nodename'])

        # "Pull the plug" on the primary lustre server
        self.remote_command(
            primary_host['config']['host'],
            primary_host['config']['destroy_command']
        )

        # Wait for failover to occur
        self.wait_until_true(lambda: self.targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state))
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

        self.wait_for_host_to_boot(
            booting_host = primary_host,
            available_host = secondary_host
        )

        # Verify did not auto-failback
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

    def chroma_controlled_failover(self, primary_host, secondary_host, filesystem_id, volumes_expected_hosts_in_normal_state, volumes_expected_hosts_in_failover_state):
        """
        Works like failover(), except that instead of killing the primary host to simulate
        an unexpected loss of a server, this uses chroma to failover a server intentionally.
        (ex use case: someone needs to service the primary server)
        """
        response = self.chroma_manager.get(
            '/api/target/',
            params = {'filesystem_id': filesystem_id}
        )
        self.assertTrue(response.successful, response.text)
        targets_running_on_primary_host = [t for t in response.json['objects']
            if t['active_host'] == primary_host['resource_uri']]

        failover_target_command_ids = []
        for target in targets_running_on_primary_host:
            response = self.chroma_manager.post(
                '/api/command/',
                body = {
                    'jobs': [{'class_name':'FailoverTargetJob',
                              'args': {'target_id': target['id']}}],
                    'message': "Failing %s over to secondary" % target['label']
                }
            )
            self.assertEqual(response.successful, True, response.text)
            command = response.json
            failover_target_command_ids.append(command['id'])

        self.wait_for_commands(self.chroma_manager, failover_target_command_ids)

        # Wait for failover to occur
        self.wait_until_true(lambda: self.targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state))
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

        self.wait_for_host_to_boot(
            booting_host = primary_host,
            available_host = secondary_host
        )

        # Verify did not auto-failback
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

    def failback(self, primary_host, filesystem_id, volumes_expected_hosts_in_normal_state):
        """
        Trigger failback for all failed over targets with primary_host as their primary server
        and verifies after that volumes are running back in their expected locations.
        """
        response = self.chroma_manager.get(
            '/api/target/',
            params = {'filesystem_id': filesystem_id}
        )
        self.assertTrue(response.successful, response.text)
        targets_with_matching_primary_host = [t for t in response.json['objects']
            if t['primary_server'] == primary_host['resource_uri']]

        failback_target_command_ids = []
        for target in targets_with_matching_primary_host:
            response = self.chroma_manager.post("/api/command/", body = {
                'jobs': [{'class_name': 'FailbackTargetJob',
                          'args': {'target_id': target['id']}}],
                'message': "Failing %s back to primary" % target['label']
            })
            self.assertEqual(response.successful, True, response.text)
            command = response.json
            failback_target_command_ids.append(command['id'])

        self.wait_for_commands(self.chroma_manager, failback_target_command_ids)

        # Wait for the targets to move back to their original server.
        self.wait_until_true(lambda: self.targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state))
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state)

    def wait_for_host_to_boot(self, booting_host, available_host):
        """
        Wait for the stonithed server to come back online
        """
        running_time = 0
        while running_time < TEST_TIMEOUT:
            try:
                #TODO: Better way to check this?
                self.remote_command(
                    booting_host['address'],
                    "echo 'Checking if node is ready to receive commands.'"
                )
            except socket.error:
                continue
            finally:
                time.sleep(3)
                running_time += 3

            # Verify other host knows it is no longer offline
            result = self.remote_command(
                available_host['address'],
                "crm node show %s" % booting_host['nodename']
            )
            node_status = result.stdout.read()
            if not re.search('offline', node_status):
                break

        self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for host to come back online.")
        result = self.remote_command(
            available_host['address'],
            "crm node show %s" % booting_host['nodename']
        )
        self.assertNotRegexpMatches(result.stdout.read(), 'offline')

    def targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts):
        """
        Determine if the targets associated with each volume is running on the expected host.

        Use this version of this check if you want test execution to continue
        and just want a boolean to check if it is as expected.
        """
        return self._check_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_to_expected_hosts, assert_true = False)

    def verify_targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts):
        """
        Assert targets associated with each volume is running on the expected host.

        Use this version of this check if you expect the targets to be on their
        proper hosts already and want test execution to be halted if not.
        """
        return self._check_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_to_expected_hosts, assert_true = True)

    def _check_targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts, assert_true):
        """
        Private function providing shared logic for public facing target active host checks.
        """
        response = self.chroma_manager.get(
            '/api/target/',
            params = {
                'filesystem_id': filesystem_id,
            }
        )
        self.assertTrue(response.successful, response.text)
        targets = response.json['objects']

        for target in targets:
            if target['volume']['id'] in volumes_to_expected_hosts:

                expected_host = volumes_to_expected_hosts[target['volume']['id']]

                # Check chroma manager thinks it's running on the right host.
                if assert_true:

                    self.assertEqual(expected_host['resource_uri'], target['active_host'])
                else:
                    if not expected_host['resource_uri'] == target['active_host']:
                        return False

                # Check pacemaker thinks it's running on the right host.
                expected_resource_status = "%s is running on: %s" % (target['ha_label'], expected_host)
                actual_resource_status = self.get_crm_resource_status(target['ha_label'], expected_host)
                if assert_true:
                    self.assertRegexpMatches(
                        actual_resource_status,
                        expected_resource_status
                    )
                else:
                    if not re.search(expected_resource_status, actual_resource_status):
                        return False

        return True

    def get_crm_resource_status(self, ha_label, expected_host):
        result = self.remote_command(
            expected_host,
            'crm resource status %s' % ha_label,
            timeout = 30  # shorter timeout since shouldnt take long and increases turnaround when there is a problem
        )
        resource_status = result.stdout.read()

        # Sometimes crm resource status gives a false positive when it is repetitively
        # trying to restart a resource over and over. Lets also check the failcount
        # to check that it didn't have problems starting.
        result = self.remote_command(
            expected_host,
            'crm resource failcount %s show %s' % (ha_label, expected_host)
        )
        self.assertRegexpMatches(
            result.stdout.read(),
            'value=0'
        )

        return resource_status
