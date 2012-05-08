import re
import socket
import time

from testconfig import config

from tests.utils.http_requests import AuthorizedHttpRequests
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.testcases import ChromaIntegrationTestCase


class TestManagedFilesystemWithFailover(ChromaIntegrationTestCase):
    def setUp(self):
        user = config['chroma_managers'][0]['users'][0]
        self.chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
                server_http_url = config['chroma_managers'][0]['server_http_url'])
        self.reset_cluster(self.chroma_manager)

    def test_create_filesystem_with_failover(self):
        # Add hosts as managed hosts
        self.assertGreaterEqual(len(config['lustre_servers']), 4)
        hosts = self.add_hosts([h['address'] for h in config['lustre_servers'][:4]])

        # Count how many of the reported Luns are ready for our test
        # (i.e. they have both a primary and a secondary node)
        ha_volumes = self.get_shared_volumes()
        self.assertGreaterEqual(len(ha_volumes), 4)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volume_1 = ha_volumes[2]
        ost_volume_2 = ha_volumes[3]

        # Set primary and secondary mounts explicitly and check they
        # are respected
        self.set_volume_mounts(mgt_volume, hosts[0]['id'], hosts[1]['id'])
        self.set_volume_mounts(mdt_volume, hosts[0]['id'], hosts[1]['id'])
        self.set_volume_mounts(ost_volume_1, hosts[2]['id'], hosts[3]['id'])
        self.set_volume_mounts(ost_volume_2, hosts[3]['id'], hosts[2]['id'])

        response = self.chroma_manager.get(
            '/api/volume/',
            params = {'category': 'usable'}
        )
        self.assertEqual(response.successful, True, response.text)
        volumes = response.json['objects']
        refreshed_mgt_volume = None
        refreshed_mdt_volume = None
        refreshed_ost_volume_1 = None
        refreshed_ost_volume_2 = None
        for volume in volumes:
            if volume['id'] == mgt_volume['id']:
                refreshed_mgt_volume = volume
            elif volume['id'] == mdt_volume['id']:
                refreshed_mdt_volume = volume
            elif volume['id'] == ost_volume_1['id']:
                refreshed_ost_volume_1 = volume
            elif volume['id'] == ost_volume_2['id']:
                refreshed_ost_volume_2 = volume
        self.assertTrue(refreshed_mgt_volume and refreshed_mdt_volume and refreshed_ost_volume_1 and refreshed_ost_volume_2)
        self.verify_volume_mounts(refreshed_mgt_volume, hosts[0]['id'], hosts[1]['id'])
        self.verify_volume_mounts(refreshed_mdt_volume, hosts[0]['id'], hosts[1]['id'])
        self.verify_volume_mounts(refreshed_ost_volume_1, hosts[2]['id'], hosts[3]['id'])
        self.verify_volume_mounts(refreshed_ost_volume_2, hosts[3]['id'], hosts[2]['id'])

        # Double check our system is ready for a filesystem to be created.
        self.verify_usable_luns_valid(ha_volumes, 4)
        self.remote_command(
            hosts[2]['address'],
            'lctl ping %s' % hosts[0]['address']
        )
        self.remote_command(
            hosts[3]['address'],
            'lctl ping %s' % hosts[0]['address']
        )

        # Create new filesystem
        filesystem_id = self.create_filesystem(
            {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {'volume_id': mdt_volume['id'], 'conf_params': {}},
                'osts': [{'volume_id': v['id'], 'conf_params': {}} for v in [ost_volume_1, ost_volume_2]],
                'conf_params': {}
            }

        )

        # Define where we expect targets for volumes to be started on depending on our failover state.
        volumes_expected_hosts_in_normal_state = {
            mgt_volume['id']: hosts[0]['nodename'],
            mdt_volume['id']: hosts[0]['nodename'],
            ost_volume_1['id']: hosts[2]['nodename'],
            ost_volume_2['id']: hosts[3]['nodename'],
        }
        volumes_expected_hosts_in_failover_state = {
            mgt_volume['id']: hosts[1]['nodename'],
            mdt_volume['id']: hosts[1]['nodename'],
            ost_volume_1['id']: hosts[2]['nodename'],
            ost_volume_2['id']: hosts[3]['nodename'],
        }

        # Verify targets are started on the correct hosts
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state)

        # Mount the filesystem
        response = self.chroma_manager.get(
            '/api/filesystem/%s/' % filesystem_id,
        )
        self.assertEqual(response.successful, True, response.text)
        mount_command = response.json['mount_command']

        client = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client, "testfs", mount_command)
        try:
            self.exercise_filesystem(client, "testfs")
        finally:
            self.unmount_filesystem(client, 'testfs')

        if config['failover_is_configured']:
            for lustre_server in config['lustre_servers']:
                for host in hosts:
                    if lustre_server['nodename'] == host['nodename']:
                        host['config'] = lustre_server

            # Fail hosts[0], which is running the MGT and MDT
            self.remote_command(
                hosts[0]['config']['host'],
                hosts[0]['config']['destroy_command']
            )

            # Wait for failover to occur
            running_time = 0
            while running_time < TEST_TIMEOUT and not self.targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state):
                time.sleep(1)
                running_time += 1

            self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for failover")
            self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

            # Wait for the stonithed server to come back online
            running_time = 0
            while running_time < TEST_TIMEOUT:
                try:
                    # TODO: Better way to check this?
                    _, stdout, _ = self.remote_command(
                        hosts[0]['nodename'],
                        "echo 'Checking if node is ready to receive commands.'"
                    )
                except socket.error:
                    continue
                finally:
                    time.sleep(3)
                    running_time += 3

                # Verify other host knows it is no longer offline
                _, stdout, _ = self.remote_command(
                    hosts[1]['nodename'],
                    "crm node show %s" % hosts[0]['nodename']
                )
                node_status = stdout.read()
                if not re.search("offline", node_status):
                    break

            self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for stonithed server to come back online.")
            _, stdout, _ = self.remote_command(
                hosts[1]['nodename'],
                "crm node show %s" % hosts[0]['nodename']
            )
            self.assertNotRegexpMatches(stdout.read(), "offline")

            # Verify did not auto-failback
            self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

            # Failback
            response = self.chroma_manager.get(
                '/api/target/',
                params = {
                    'filesystem_id': filesystem_id,
                    'kind': 'MGT',
                }
            )
            self.assertTrue(response.successful, response.text)
            mgt = response.json['objects'][0]
            _, stdout, _ = self.remote_command(
                hosts[0]['nodename'],
                'chroma-agent failback-target --label %s --id %s' % (mgt['label'], mgt['id'])
            )

            response = self.chroma_manager.get(
                '/api/target/',
                params = {
                    'filesystem_id': filesystem_id,
                    'kind': 'MDT',
                }
            )
            self.assertTrue(response.successful, response.text)
            mdt = response.json['objects'][0]
            _, stdout, _ = self.remote_command(
                hosts[0]['nodename'],
                'chroma-agent failback-target --label %s --id %s' % (mdt['label'], mdt['id'])
            )

            # Wait for the targets to move back to their original server
            running_time = 0
            while running_time < TEST_TIMEOUT and not self.targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state):
                time.sleep(1)
                running_time += 1

            self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for failback")
            self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state)

            # TODO: Also add a test for failback on the active/active OSTs.
