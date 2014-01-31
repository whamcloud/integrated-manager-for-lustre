

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.failover_testcase_mixin import FailoverTestCaseMixin
from tests.integration.core.stats_testcase_mixin import StatsTestCaseMixin


class TestManagedFilesystemWithFailover(FailoverTestCaseMixin, StatsTestCaseMixin, ChromaIntegrationTestCase):
    TESTS_NEED_POWER_CONTROL = True
    TEST_SERVERS = config['lustre_servers'][0:4]

    def test_create_filesystem_with_failover(self):
        # Add hosts as managed hosts
        self.assertGreaterEqual(len(self.TEST_SERVERS), 4)
        hosts = self.add_hosts([s['address'] for s in self.TEST_SERVERS])

        # Set up power control for fencing -- needed to ensure that
        # failover completes. Pacemaker won't fail over the resource
        # if it can't STONITH the primary.
        if config['failover_is_configured']:
            self.configure_power_control()

        # Count how many of the reported Luns are ready for our test
        # (i.e. they have both a primary and a failover node)
        ha_volumes = self.get_shared_volumes(required_hosts = 4)
        self.assertGreaterEqual(len(ha_volumes), 4)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volume_1 = ha_volumes[2]
        ost_volume_2 = ha_volumes[3]

        target_hosts = {
            'mgt': {'primary': hosts[0], 'failover': hosts[1]},
            'mdt': {'primary': hosts[1], 'failover': hosts[0]},
            'ost1': {'primary': hosts[2], 'failover': hosts[3]},
            'ost2': {'primary': hosts[3], 'failover': hosts[2]},
        }

        # Set primary and failover mounts explicitly and check they
        # are respected
        self.set_volume_mounts(
            mgt_volume,
            target_hosts['mgt']['primary']['id'],
            target_hosts['mgt']['failover']['id']
        )
        self.set_volume_mounts(
            mdt_volume,
            target_hosts['mdt']['primary']['id'],
            target_hosts['mdt']['failover']['id']
        )
        self.set_volume_mounts(
            ost_volume_1,
            target_hosts['ost1']['primary']['id'],
            target_hosts['ost1']['failover']['id']
        )
        self.set_volume_mounts(
            ost_volume_2,
            target_hosts['ost2']['primary']['id'],
            target_hosts['ost2']['failover']['id']
        )

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
        self.verify_volume_mounts(
            refreshed_mgt_volume,
            target_hosts['mgt']['primary']['id'],
            target_hosts['mgt']['failover']['id']
        )
        self.verify_volume_mounts(
            refreshed_mdt_volume,
            target_hosts['mdt']['primary']['id'],
            target_hosts['mdt']['failover']['id']
        )
        self.verify_volume_mounts(
            refreshed_ost_volume_1,
            target_hosts['ost1']['primary']['id'],
            target_hosts['ost1']['failover']['id']
        )
        self.verify_volume_mounts(
            refreshed_ost_volume_2,
            target_hosts['ost2']['primary']['id'],
            target_hosts['ost2']['failover']['id']
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
            mgt_volume['id']: target_hosts['mgt']['primary'],
            mdt_volume['id']: target_hosts['mdt']['primary'],
            ost_volume_1['id']: target_hosts['ost1']['primary'],
            ost_volume_2['id']: target_hosts['ost2']['primary'],
        }

        # Verify targets are started on the correct hosts
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_normal_state)

        # Mount the filesystem
        filesystem = self.get_filesystem(filesystem_id)
        self.assertTrue(filesystem['mount_command'])

        client = config['lustre_clients'][0]['address']
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_operations.exercise_filesystem(client, filesystem)
            self.check_stats(filesystem_id)
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

        # Test failover if the cluster config indicates that failover has
        # been properly configured with stonith, etc.
        if config['failover_is_configured']:
            # Test MGS failover
            volumes_expected_hosts_in_failover_state = {
                mgt_volume['id']: target_hosts['mgt']['failover'],
                mdt_volume['id']: target_hosts['mdt']['primary'],
                ost_volume_1['id']: target_hosts['ost1']['primary'],
                ost_volume_2['id']: target_hosts['ost2']['primary'],
            }

            self.failover(
                target_hosts['mgt']['primary'],
                target_hosts['mgt']['failover'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state
            )

            self.failback(
                target_hosts['mgt']['primary'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state
            )

            # Test MDS failover
            volumes_expected_hosts_in_failover_state = {
                mgt_volume['id']: target_hosts['mgt']['primary'],
                mdt_volume['id']: target_hosts['mdt']['failover'],
                ost_volume_1['id']: target_hosts['ost1']['primary'],
                ost_volume_2['id']: target_hosts['ost2']['primary'],
            }

            self.failover(
                target_hosts['mdt']['primary'],
                target_hosts['mdt']['failover'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state
            )

            self.failback(
                target_hosts['mdt']['primary'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state
            )

            # Test failing over an OSS
            volumes_expected_hosts_in_failover_state = {
                mgt_volume['id']: target_hosts['mgt']['primary'],
                mdt_volume['id']: target_hosts['mdt']['primary'],
                ost_volume_1['id']: target_hosts['ost1']['failover'],
                ost_volume_2['id']: target_hosts['ost2']['primary'],
            }

            self.failover(
                target_hosts['ost1']['primary'],
                target_hosts['ost1']['failover'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state
            )

            self.failback(
                target_hosts['ost1']['primary'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state
            )

            # Test failing over an OSS using chroma to do a controlled failover
            volumes_expected_hosts_in_failover_state = {
                mgt_volume['id']: target_hosts['mgt']['primary'],
                mdt_volume['id']: target_hosts['mdt']['primary'],
                ost_volume_1['id']: target_hosts['ost1']['primary'],
                ost_volume_2['id']: target_hosts['ost2']['failover'],
            }

            self.chroma_controlled_failover(
                target_hosts['ost2']['primary'],
                target_hosts['ost2']['failover'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state,
                volumes_expected_hosts_in_failover_state
            )

            self.failback(
                target_hosts['ost2']['primary'],
                filesystem_id,
                volumes_expected_hosts_in_normal_state
            )

    def test_lnet_operational_after_failover(self):
        self.remote_operations.reset_server(self.TEST_SERVERS[0]['fqdn'])
        self.remote_operations.await_server_boot(self.TEST_SERVERS[0]['fqdn'])

        # Add two hosts
        host_1 = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]
        host_2 = self.add_hosts([self.TEST_SERVERS[1]['address']])[0]

        # Set volume mounts
        ha_volumes = self.get_shared_volumes()
        self.assertGreaterEqual(len(ha_volumes), 4)
        self.set_volume_mounts(ha_volumes[0], host_1['id'], host_2['id'])
        self.set_volume_mounts(ha_volumes[1], host_1['id'], host_2['id'])
        self.set_volume_mounts(ha_volumes[2], host_2['id'], host_1['id'])
        self.set_volume_mounts(ha_volumes[3], host_2['id'], host_1['id'])

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
