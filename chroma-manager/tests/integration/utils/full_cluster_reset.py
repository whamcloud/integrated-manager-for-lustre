from tests.integration.core.testcases import ChromaIntegrationTestCase


class FullyResetCluster(ChromaIntegrationTestCase):
    def test_fully_reset_cluster(self):
        """
        Fully resetting the cluster and recreating the chroma db.
        """
        self.reset_cluster()
