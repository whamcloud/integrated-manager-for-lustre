from testconfig import config

from tests.utils.http_requests import HttpRequests
from tests.integration.core.testcases import ChromaIntegrationTestCase


class VerifyClusterNotConfigured(ChromaIntegrationTestCase):

    def test_cluster_not_configured(self):
        for hydra_server_config in config['hydra_servers']:
            hydra_server = HttpRequests(
                server_http_url=hydra_server_config['server_http_url']
            )
            self.verify_cluster_not_configured(hydra_server, config['lustre_servers'])
