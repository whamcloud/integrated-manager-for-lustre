from mock import patch
from chroma_agent.action_plugins.manage_node import shutdown_server, reboot_server
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from .test_manage_target import CommandCaptureTestCase


class TestServerShutdownAndReboot(CommandCaptureTestCase):
    @patch('os._exit')
    def test_server_shutdown(self, os__exit):
        run_args = ['shutdown', '-H', 'now']
        self.results = {tuple(run_args): (0, "", "")}

        try:
            shutdown_server()
        except CallbackAfterResponse, e:
            e.callback()
        self.assertRan(run_args)

        self.assertTrue(os__exit.called)

    @patch('os._exit')
    def test_server_reboot(self, os__exit):
        run_args = ['shutdown', '-r', 'now']
        self.results = {tuple(run_args): (0, "", "")}

        try:
            reboot_server()
        except CallbackAfterResponse, e:
            e.callback()
        self.assertRan(run_args)

        self.assertTrue(os__exit.called)
