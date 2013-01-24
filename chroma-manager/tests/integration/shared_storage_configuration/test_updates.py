from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestWriteconf(ChromaIntegrationTestCase):
    def setUp(self):
        super(TestWriteconf, self).setUp()
        self.host = self.add_hosts([config['lustre_servers'][-1]['address']])

    def test_update_hosts(self):
        resp = self.chroma_manager.post("/api/command/", body = {
                   'jobs': [{'class_name': 'UpdateJob', 'args': {}}],
                   'message': "Update packages"})

        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.json['errored'])
        self.wait_for_command(self.chroma_manager, resp.json['id'])
