from mock import patch

from chroma_agent.action_plugins.manage_node import shutdown_server, reboot_server
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from emf_common.test.command_capture_testcase import CommandCaptureTestCase


class TestServerShutdownAndReboot(CommandCaptureTestCase):
    @patch("os._exit")
    def test_server_shutdown(self, os__exit):
        run_args = ("shutdown", "-H", "now")
        self.add_command(run_args)

        try:
            shutdown_server()
        except CallbackAfterResponse as e:
            e.callback()
        self.assertRanAllCommandsInOrder()

        self.assertTrue(os__exit.called)

    @patch("os._exit")
    def test_server_reboot(self, os__exit):
        run_args = ("shutdown", "-r", "now")
        self.add_command(run_args)

        try:
            reboot_server()
        except CallbackAfterResponse as e:
            e.callback()
        self.assertRanAllCommandsInOrder()
        self.assertTrue(os__exit.called)
