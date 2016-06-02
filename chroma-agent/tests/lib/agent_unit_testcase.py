import mock

from django.utils import unittest

from chroma_agent.chroma_common.lib.agent_rpc import agent_error, agent_result_ok


class AgentUnitTestCase(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)

    def assertAgentOK(self, value):
        self.assertEqual(value, agent_result_ok)

    def assertAgentError(self, value, message):
        self.assertEqual(value, agent_error(message))
