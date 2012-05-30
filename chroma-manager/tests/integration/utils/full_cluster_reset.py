from testconfig import config

from tests.integration.core.testcases import ChromaIntegrationTestCase
from tests.utils.http_requests import AuthorizedHttpRequests


class FullyResetCluster(ChromaIntegrationTestCase):
    def test_fully_reset_cluster(self):
        """
        Fully resetting the cluster and recreating the chroma db.
        """
        user = config['chroma_managers'][0]['users'][0]
        for chroma_manager in config['chroma_managers']:
            chroma_manager = AuthorizedHttpRequests(
                user['username'],
                user['password'],
                server_http_url = chroma_manager['server_http_url']
            )
            self.reset_cluster(chroma_manager)
            self.reset_chroma_manager_db(user)
