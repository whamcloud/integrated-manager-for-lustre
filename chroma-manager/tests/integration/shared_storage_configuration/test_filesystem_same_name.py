
from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestFilesystemSameNameHYD832(ChromaIntegrationTestCase):
    def test_same_name(self):
        """
        Test that creating a filesystem with the same name as a
        previously removed filesystem on the same MGS.
        """
        self.assertGreaterEqual(len(config['lustre_servers'][0]['device_paths']), 5)

        reused_name = 'testfs'
        other_name = 'foofs'

        # The test uses a custom filesystem creation using 3 disks instead of the
        # usual 4 because we need the other 2 disks for later in the test.
        servers = [s['address'] for s in self.TEST_SERVERS[:4]]
        hosts = self.add_hosts(servers)
        self.configure_power_control(servers)

        ha_volumes = self.wait_for_shared_volumes(5, 4)

        self.set_volume_mounts(ha_volumes[0], hosts[0]['id'], hosts[1]['id'])
        self.set_volume_mounts(ha_volumes[1], hosts[1]['id'], hosts[0]['id'])
        self.set_volume_mounts(ha_volumes[2], hosts[2]['id'], hosts[3]['id'])
        self.set_volume_mounts(ha_volumes[3], hosts[0]['id'], hosts[1]['id'])
        self.set_volume_mounts(ha_volumes[4], hosts[3]['id'], hosts[2]['id'])

        fs_id = self.create_filesystem({'name': reused_name,
                                        'mgt': {'volume_id': ha_volumes[0]['id']},
                                        'mdts': [{'volume_id': ha_volumes[1]['id'],
                                                  'conf_params': {}}],
                                        'osts': [{'volume_id': ha_volumes[2]['id'],
                                                  'conf_params': {}}],
                                        'conf_params': {}})

        fs = self.chroma_manager.get("/api/filesystem/%s/" % fs_id,
                                     params={'dehydrate__osts': True}).json
        mgt_id = fs['mgt']['id']

        def create_for_mgs(name, reformat=False):
            ha_volumes = self.wait_for_shared_volumes(2, 4)

            mdt_volume = ha_volumes[0]
            ost_volumes = [ha_volumes[1]]
            return self.create_filesystem({'name': name,
                                           'mgt': {'id': mgt_id},
                                           'mdts': [{'volume_id': mdt_volume['id'],
                                                     'conf_params': {},
                                                     'reformat': reformat}],
                                           'osts': [{'volume_id': v['id'],
                                                     'conf_params': {},
                                                     'reformat': reformat} for v in ost_volumes],
                                           'conf_params': {}})

        other_fs_id = create_for_mgs(other_name)

        response = self.chroma_manager.delete(fs['resource_uri'])
        self.assertEqual(response.status_code, 202)
        self.wait_for_command(self.chroma_manager, response.json['command']['id'])

        # Now remove any zfs datasets, this is a topic to be discussed, but until we remove the datasets
        # we cannot create a new filesystem. If IML does it directly as part of remove filesystem which it could
        # then removing the filesystem would be truly unrecoverable and people might not like that.
        datasets = [ost['volume']['volume_nodes'][0]['path'] for ost in fs['osts']]
        datasets.extend([mdt['volume']['volume_nodes'][0]['path'] for mdt in fs['mdts']])

        # Filter out the paths by removing anything with a leading /.
        datasets = [dataset for dataset in datasets if dataset.startswith('/') is False]

        self.cleanup_zfs_pools(self.TEST_SERVERS[:2],
                               self.CZP_REMOVEDATASETS | self.CZP_EXPORTPOOLS,
                               datasets,
                               True)

        # Our other FS should be untouched
        self.assertEqual(len(self.chroma_manager.get("/api/filesystem/").json['objects']), 1)
        self.assertState("/api/filesystem/%s/" % other_fs_id, 'available')

        reused_fs_id = create_for_mgs(reused_name, reformat=True)

        self.assertState("/api/filesystem/%s/" % reused_fs_id, 'available')
        self.assertState("/api/filesystem/%s/" % other_fs_id, 'available')

        self.graceful_teardown(self.chroma_manager)
