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
        self.reset_cluster(self.chroma_manager, self.user)

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

        # Create new filesystem
        self.verify_usable_luns_valid(ha_volumes, 4)
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
            self.failover(
                hosts[0],
                hosts[1],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state
            )

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
                'chroma-agent failback-target --ha_label %s' % mgt['ha_label']
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
                'chroma-agent failback-target --ha_label %s' % mdt['ha_label']
            )

            # Wait for the targets to move back to their original server
            running_time = 0
            while running_time < TEST_TIMEOUT and not self.targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state):
                time.sleep(1)
                running_time += 1

            self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for failback")
            self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state)

            # TODO: Also add a test for failback on the active/active OSTs.

    def test_lnet_operational_after_failover(self):
        if config['failover_is_configured']:
            # "Pull the plug" on host
            self.remote_command(
                config['lustre_servers'][0]['host'],
                config['lustre_servers'][0]['destroy_command']
            )

            # Wait for host to boot back up
            self.wait_for_host_to_boot(
                booting_host = config['lustre_servers'][0],
                available_host = config['lustre_servers'][2]
            )

            # Add two hosts
            host_1 = self.add_hosts([config['lustre_servers'][0]['address']])[0]
            host_2 = self.add_hosts([config['lustre_servers'][1]['address']])[0]

            # Set volume mounts
            ha_volumes = self.get_shared_volumes()
            self.assertGreaterEqual(len(ha_volumes), 4)
            self.set_volume_mounts(ha_volumes[0], host_1['id'], host_2['id'])
            self.set_volume_mounts(ha_volumes[1], host_1['id'], host_2['id'])
            self.set_volume_mounts(ha_volumes[2], host_2['id'], host_1['id'])
            self.set_volume_mounts(ha_volumes[3], host_2['id'], host_1['id'])
            self.verify_usable_luns_valid(ha_volumes, 4)

            # Create new filesystem such that the mgs/mdt is on the host we
            # failed over and the osts are not.
            self.create_filesystem(
                {
                    'name': 'testfs',
                    'mgt': {'volume_id': ha_volumes[0]['id']},
                    'mdt': {'volume_id': ha_volumes[1]['id'], 'conf_params': {}},
                    'osts': [{'volume_id': v['id'], 'conf_params': {}} for v in ha_volumes[2:3]],
                    'conf_params': {}
                }
            )
