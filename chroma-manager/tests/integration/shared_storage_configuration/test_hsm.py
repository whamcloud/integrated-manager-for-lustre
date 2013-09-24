from testconfig import config

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestHsmCoordinatorControl(ChromaIntegrationTestCase):
    def _create_with_params(self, enabled=False):
        self.hosts = self.add_hosts([
            config['lustre_servers'][0]['address'],
            config['lustre_servers'][1]['address']
        ])

        # Since the test code seems to rely on this ordering, we should
        # check for it right away and blow up if it's not as we expect.
        self.assertEqual([h['address'] for h in self.hosts],
                         [config['lustre_servers'][0]['address'],
                          config['lustre_servers'][1]['address']])

        volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(volumes), 4)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volume = volumes[2]
        host_ids = [h['id'] for h in self.hosts]
        self.set_volume_mounts(mgt_volume, *host_ids)
        self.set_volume_mounts(mdt_volume, *host_ids)
        self.set_volume_mounts(ost_volume, *host_ids)

        if enabled:
            mdt_params = {'mdt.hsm_control': 'enabled'}
        else:
            mdt_params = {'mdt.hsm_control': 'disabled'}

        self.filesystem_id = self.create_filesystem(
                {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': mdt_params

                },
                'osts': [{
                    'volume_id': ost_volume['id'],
                    'conf_params': {'ost.writethrough_cache_enable': '0'}
                }],
                'conf_params': {'llite.max_cached_mb': '16'}
            }
        )

    def _test_params(self):
        mds = config['lustre_servers'][0]['address']
        self.wait_until_true(lambda: "enabled" == self.remote_operations.read_proc(mds, "/proc/fs/lustre/mdt/testfs-MDT0000/hsm_control"))

    def test_creation_conf_params(self):
        self._create_with_params(enabled=True)
        self._test_params()
        self.graceful_teardown(self.chroma_manager)
