from testconfig import config

from tests.utils.http_requests import HttpRequests
from tests.integration.core.testcases import ChromaIntegrationTestCase


class VerifyClusterNotConfigured(ChromaIntegrationTestCase):

    def test_cluster_not_configured(self):
        for chroma_manager_config in config['chroma_managers']:
            chroma_manager = HttpRequests(
                server_http_url=chroma_manager_config['server_http_url']
            )
            self.verify_cluster_not_configured(chroma_manager, config['lustre_servers'])
