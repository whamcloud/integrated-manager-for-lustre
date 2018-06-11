from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class FullyResetCluster(ChromaIntegrationTestCase):
    """
    Small convenience utility for completely wiping out a test cluster.

    Will fully wipe a test cluster, including dropping and recreating the
    manager database, unconfiguring and chroma targets in pacemaker,
    and erasing any volumes in the config for managed servers.
    """

    def test_fully_reset_cluster(self):
        """
        Fully resetting the cluster and recreating the chroma db.
        """
        self.reset_cluster()
