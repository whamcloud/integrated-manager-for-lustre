from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestTargets(ChromaIntegrationTestCase):
    """Exercise target operations done via the /api/target/
    (this is a separate path to the typical filesystem ops done via /api/filesystem/)"""

    def test_create_mgt(self):
        self.add_hosts([config['lustre_servers'][0]['address']])
        volumes = self.get_usable_volumes()

        response = self.chroma_manager.post("/api/target/", body = {
            'volume_id': volumes[0]['id'],
            'kind': 'MGT'
        })

        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json['target']['resource_uri']
        create_command = response.json['command']['id']
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, 'mounted')

        self.set_state(target_uri, 'unmounted')
        self.set_state(target_uri, 'mounted')

        response = self.chroma_manager.delete(target_uri)
        self.assertEqual(response.status_code, 202)
        delete_command = response.json['command']
        self.wait_for_command(self.chroma_manager, delete_command['id'])

    def test_create_ost(self):
        filesystem_id = self.create_filesystem_simple()
        filesystem_uri = "/api/filesystem/%s/" % filesystem_id

        volume = self.get_usable_volumes()[0]
        response = self.chroma_manager.post("/api/target/", body = {
            'volume_id': volume['id'],
            'kind': 'OST',
            'filesystem_id': filesystem_id
        })
        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json['target']['resource_uri']
        create_command = response.json['command']['id']
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, 'mounted')
        self.assertState(filesystem_uri, 'available')

        self.set_state(target_uri, 'unmounted')
        self.assertState(filesystem_uri, 'unavailable')
        self.set_state(target_uri, 'mounted')
        self.assertState(filesystem_uri, 'available')

        response = self.chroma_manager.delete(target_uri)
        self.assertEqual(response.status_code, 202)
        delete_command = response.json['command']
        self.wait_for_command(self.chroma_manager, delete_command['id'])
