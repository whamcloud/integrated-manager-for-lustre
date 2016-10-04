from chroma_agent.lib.agent_startup_functions import agent_daemon_startup_functions
from chroma_agent.action_plugins.manage_node import initialise_block_device_drivers
from tests.lib.agent_unit_testcase import AgentUnitTestCase


class TestManagedNode(AgentUnitTestCase):
    def test_initialise_block_device_drivers_called_at_started(self):
        self.assertTrue(initialise_block_device_drivers in agent_daemon_startup_functions)
