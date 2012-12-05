

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.shared_storage_configuration import example_api_client


class TestExampleApiClient(ChromaIntegrationTestCase):
    def test_login(self):
        self.hosts = self.add_hosts([
            config['lustre_servers'][0]['address'],
            config['lustre_servers'][1]['address']])

        example_api_client.setup_ca(config['chroma_managers'][0]['server_http_url'])
        hosts = example_api_client.list_hosts(config['chroma_managers'][0]['server_http_url'],
            config['chroma_managers'][0]['users'][0]['username'],
            config['chroma_managers'][0]['users'][0]['password']
        )
        self.assertListEqual(hosts, [h['fqdn'] for h in self.hosts])
