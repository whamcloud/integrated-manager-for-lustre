

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.remote_operations import SimulatorRemoteOperations, RealRemoteOperations


class TestInstallationAndUpgrade(ChromaIntegrationTestCase):
    TEST_SERVERS = config['lustre_servers'][0:4]

    def setUp(self):
        # Create a nice standardized filesystem name to use.
        self.fs_name = "testfs"

        # connect the remote operations but otherwise...
        if config.get('simulator', False):
            self.remote_operations = SimulatorRemoteOperations(self, self.simulator)
        else:
            self.remote_operations = RealRemoteOperations(self)

        # Enable agent debugging
        self.remote_operations.enable_agent_debug(self.TEST_SERVERS)

        self.wait_until_true(self.supervisor_controlled_processes_running)
        self.initial_supervisor_controlled_process_start_times = self.get_supervisor_controlled_process_start_times()
