from mock import patch
from chroma_agent.action_plugins.manage_node import shutdown_server, reboot_server
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from .test_manage_target import CommandCaptureTestCase


class TestServerShutdownAndReboot(CommandCaptureTestCase):
    @patch('os._exit')
    def test_server_shutdown(self, os__exit):
        try:
            shutdown_server()
        except CallbackAfterResponse, e:
            e.callback()
        self.assertRan(['shutdown', '-H', 'now'])

        self.assertTrue(os__exit.called)

    @patch('os._exit')
    def test_server_reboot(self, os__exit):
        try:
            reboot_server()
        except CallbackAfterResponse, e:
            e.callback()
        self.assertRan(['shutdown', '-r', 'now'])

        self.assertTrue(os__exit.called)
