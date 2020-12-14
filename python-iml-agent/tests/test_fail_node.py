from chroma_agent.action_plugins.manage_fail_node import fail_node
from iml_common.test.command_capture_testcase import (
    CommandCaptureTestCase,
    CommandCaptureCommand,
)


class TestConfParams(CommandCaptureTestCase):
    def test_failnode(self):
        self.add_commands(
            CommandCaptureCommand(("sync",), 0, "", ""),
            CommandCaptureCommand(("sync",), 0, "", ""),
            CommandCaptureCommand(("init", "0"), 0, "", ""),
        )

        fail_node([])
        self.assertRanAllCommandsInOrder()
