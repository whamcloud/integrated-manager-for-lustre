import time
from chroma_agent.agent_client import HttpWriter, Message
from django.utils import unittest
import mock


class TestHttpWriter(unittest.TestCase):
    def test_message_callback(self):
        """Test that when a callback is included in a Message(), it is invoked
        after the message is sent"""

        client = mock.Mock()
        client._fqdn = "test_server"

        callback = mock.Mock()

        # Disable poll() so that it's not trying to set up sessions, just doing passthrough of messages
        with mock.patch("chroma_agent.agent_client.HttpWriter.poll"):
            writer = HttpWriter(client)
            writer.start()

            message = Message("DATA", "test_plugin", {'key1': 'val1'}, 'session_foo', 666, callback = callback)
            writer.put(message)

            TIMEOUT = 2
            i = 0
            while True:
                if client.post.call_count and callback.call_count:
                    break
                else:
                    time.sleep(1)
                    i += 1
                    if i > TIMEOUT:
                        raise RuntimeError("Timeout waiting for .post() and callback (%s %s)" % (client.post.call_count, callback.call_count))

            # Should have sent back the result
            self.assertEqual(client.post.call_count, 1)
            self.assertDictEqual(client.post.call_args[0][0], {'messages': [message.dump(client._fqdn)]})

            # Should have invoked the callback
            self.assertEqual(callback.call_count, 1)

            writer.stop()
            writer.join()
