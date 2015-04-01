

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestFilesystemSameName_HYD832(ChromaIntegrationTestCase):
    def test_same_name(self):
        """
        Test that creating a filesystem with the same name as a
        previously removed filesystem on the same MGS.
        """
        self.assertGreaterEqual(len(config['lustre_servers'][0]['device_paths']), 5)

        reused_name = 'testfs'
        other_name = 'foofs'

        fs_id = self.create_filesystem_simple(name = reused_name)

        fs = self.chroma_manager.get("/api/filesystem/%s/" % fs_id).json
        mgt_id = fs['mgt']['id']

        def create_for_mgs(name, reformat=False):
            ha_volumes = self.get_usable_volumes()
            self.assertGreaterEqual(len(ha_volumes), 2)

            mdt_volume = ha_volumes[0]
            ost_volumes = [ha_volumes[1]]
            return self.create_filesystem(
                    {
                    'name': name,
                    'mgt': {'id': mgt_id},
                    'mdts': [{
                        'volume_id': mdt_volume['id'],
                        'conf_params': {},
                        'reformat': reformat
                    }],
                    'osts': [{
                        'volume_id': v['id'],
                        'conf_params': {},
                        'reformat': reformat
                    } for v in ost_volumes],
                    'conf_params': {},
                }
            )

        other_fs_id = create_for_mgs(other_name)

        response = self.chroma_manager.delete(fs['resource_uri'])
        self.assertEqual(response.status_code, 202)
        self.wait_for_command(self.chroma_manager, response.json['command']['id'])

        # Our other FS should be untouched
        self.assertEqual(len(self.chroma_manager.get("/api/filesystem/").json['objects']), 1)
        self.assertState("/api/filesystem/%s/" % other_fs_id, 'available')

        reused_fs_id = create_for_mgs(reused_name, reformat=True)

        self.assertState("/api/filesystem/%s/" % reused_fs_id, 'available')
        self.assertState("/api/filesystem/%s/" % other_fs_id, 'available')

        self.graceful_teardown(self.chroma_manager)
