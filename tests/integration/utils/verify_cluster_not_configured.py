from testconfig import config

from tests.utils.http_requests import HttpRequests

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class VerifyClusterNotConfigured(ChromaIntegrationTestCase):
    """
    Small utility for verifying that a cluster has no managed targets.
    """

    def test_cluster_not_configured(self):
        """Verifying the cluster has no managed targets."""
        for chroma_manager_config in config["chroma_managers"]:
            chroma_manager = HttpRequests(server_http_url=chroma_manager_config["server_http_url"])
            self.assertDatabaseClear(chroma_manager)
