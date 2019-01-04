from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.remote_operations import RealRemoteOperations


class TestInstallationAndUpgrade(ChromaIntegrationTestCase):
    def setUp(self):
        # Create a nice standardized filesystem name to use.
        self.fs_name = "testfs"

        self.remote_operations = RealRemoteOperations(self)

        # Enable agent debugging
        self.remote_operations.enable_agent_debug(self.TEST_SERVERS)
