from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestAutodetection(ChromaIntegrationTestCase):
    TEST_SERVERS = [config['lustre_servers'][0]]

    def test_simple_detection(self):
        self.create_filesystem_simple()
        host_id = self.chroma_manager.get("/api/host/").json['objects'][0]['id']
        mgt = self.chroma_manager.get("/api/filesystem/").json['objects'][0]['mgt']

        existing_targets = self.remote_operations.backup_cib(self.TEST_SERVERS[0])

        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host_id}}],
            'message': "Test force remove hosts"
        }).json

        self.wait_for_command(self.chroma_manager, command['id'])

        self.assertEqual(len(self.chroma_manager.get("/api/host/").json['objects']), 0)

        self.add_hosts([self.TEST_SERVERS[0]['address']])

        self.remote_operations.restore_cib(self.TEST_SERVERS[0], existing_targets)

        response = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'DetectTargetsJob', 'args': {}}],
            'message': "Test detect targets"
        })
        self.assertEqual(response.status_code, 201, response.content)
        self.wait_for_command(self.chroma_manager, response.json['id'])

        fs = self.chroma_manager.get("/api/filesystem/").json['objects'][0]
        self.assertEqual(len(fs['mdts']), 1)
        self.assertEqual(len(fs['osts']), 1)

        self.assertEqual(fs['mgt']['state'], 'mounted')

        fqdn = self.TEST_SERVERS[0]['fqdn']
        self.remote_operations.stop_target(fqdn, mgt['ha_label'])

        def mgt_is_unmounted():
            fs = self.chroma_manager.get("/api/filesystem/").json['objects'][0]
            return fs['mgt']['state'] == 'unmounted'
        self.wait_until_true(mgt_is_unmounted)
