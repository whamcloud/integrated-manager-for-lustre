from chroma_core.lib.util import invoke_rust_agent
from chroma_core.lib.util import RustAgentCancellation
from chroma_core.lib.util import runningInDocker
from django.test import TestCase
import mock
import threading


@mock.patch("chroma_core.lib.util.uuid.uuid4", return_value="1-2-3-4")
@mock.patch("chroma_core.lib.util.requests_unixsocket.post")
@mock.patch("chroma_core.lib.util.requests.post")
class TestInvokeRustAgent(TestCase):
    def test_send_action(self, post, a, b):
        invoke_rust_agent("mds1.local", "ls")

        if runningInDocker():
            call = "http://127.0.0.1:8009" 
        else:
            call = "http+unix://%2Fvar%2Frun%2Fiml-action-runner.sock/"
        
        post.assert_called_once_with(
            call,
            json={"REMOTE": ("mds1.local", {"action": "ls", "args": {}, "type": "ACTION_START", "id": "1-2-3-4"})},
        )

    def test_get_data(self, post, a, b):
        post.return_value.content = "{}"

        r = invoke_rust_agent("mds1.local", "ls")

        self.assertEqual(r, "{}")

    def test_cancel(self, post, a, b):
        trigger = threading.Event()

        trigger.set()

        with self.assertRaises(RustAgentCancellation):
            invoke_rust_agent("mds1.local", "ls", {}, trigger)

    def test_error_raises(self, post, a, b):
        post.side_effect = Exception("ruh-roh")

        with self.assertRaises(Exception):
            invoke_rust_agent("mds1.local", "ls")
