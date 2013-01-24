from testconfig import config

from tests.integration.core.chroma_integration_testcase import AuthorizedTestCase


class TestVolumes(AuthorizedTestCase):
    def setUp(self):
        super(TestVolumes, self).setUp()

    def test_volumes_on_existing_filesystem_not_usable(self):
        # Create a file system.
        self.add_hosts([config['lustre_servers'][0]['address']])

        ha_volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(ha_volumes), 3)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volumes = [ha_volumes[2]]
        self.create_filesystem(
                {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': {}
                },
                'osts': [{
                    'volume_id': v['id'],
                    'conf_params': {}
                } for v in ost_volumes],
                'conf_params': {}
            }
        )
        host_id = self.chroma_manager.get("/api/host").json['objects'][0]['id']

        # Force remove the hosts (and thus the file system) so that they are
        # forgotten from the db but not actually torn down.
        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host_id}}],
            'message': "Test force remove hosts"
        }).json
        self.wait_for_command(self.chroma_manager, command['id'])
        self.assertEqual(len(self.chroma_manager.get("/api/host").json['objects']), 0)

        # Re-add the removed hosts
        self.add_hosts([config['lustre_servers'][0]['address']])

        # Verify that the used volumes aren't showing as usable volumes.
        usable_volumes_labels = [v['label'] for v in self.get_usable_volumes()]
        self.assertNotIn(mgt_volume['label'], usable_volumes_labels)
        self.assertNotIn(mdt_volume['label'], usable_volumes_labels)
        self.assertNotIn(ost_volumes[0]['label'], usable_volumes_labels)
