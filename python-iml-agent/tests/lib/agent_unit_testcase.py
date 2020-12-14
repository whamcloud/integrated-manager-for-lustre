from iml_common.lib import util
import mock

import unittest

from iml_common.lib.agent_rpc import agent_error, agent_result_ok


class AgentUnitTestCase(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)

        mock.patch.object(
            util,
            "platform_info",
            util.PlatformInfo("Linux", "CentOS", 7.2, "7.21552", 2.7, 7, "3.10.0-327.36.3.el7.x86_64"),
        ).start()

    def assertAgentOK(self, value):
        self.assertEqual(value, agent_result_ok)

    def assertAgentError(self, value, message):
        self.assertEqual(value, agent_error(message))
