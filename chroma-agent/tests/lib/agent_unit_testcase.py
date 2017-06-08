from chroma_common.lib.agent_rpc import agent_error, agent_result_ok
from chroma_common.test.iml_unit_testcase import ImlUnitTestCase


class AgentUnitTestCase(ImlUnitTestCase):
    def assertAgentOK(self, value):
        self.assertEqual(value, agent_result_ok)

    def assertAgentError(self, value, message):
        self.assertEqual(value, agent_error(message))
