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

        # Completely drop the database to ensure all knowledge of the
        # file system, volumes, and hosts is lost.
        self.reset_chroma_manager_db()
        self.login()

        # Re-add the removed hosts
        self.add_hosts([config['lustre_servers'][0]['address']])

        # Verify that the used volumes aren't showing as usable volumes.
        usable_volumes_ids = [v['id'] for v in self.get_usable_volumes()]
        self.assertNotIn(mgt_volume['id'], usable_volumes_ids)
        self.assertNotIn(mdt_volume['id'], usable_volumes_ids)
        self.assertNotIn(ost_volumes[0]['id'], usable_volumes_ids)
