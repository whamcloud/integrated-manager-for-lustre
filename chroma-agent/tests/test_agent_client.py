import time
from chroma_agent.agent_client import HttpWriter, Message
from chroma_agent.plugin_manager import PRIO_LOW, DevicePluginMessage, PRIO_NORMAL, PRIO_HIGH
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

    def test_priorities(self):
        """
        Test that messages are consumed for POST based on the priority of the payload (data plane), or at the highest
        priority if no payload (control plane)
        """

        client = mock.Mock()
        client._fqdn = "test_server"
        writer = HttpWriter(client)

        def inject_messages(*args, **kwargs):
            # A control plane message
            writer.put(Message("SESSION_CREATE_REQUEST", "plugin_fuz", None, None, None))

            low_body = DevicePluginMessage('low', PRIO_LOW)
            normal_body = DevicePluginMessage('normal', PRIO_NORMAL)
            high_body = DevicePluginMessage('high', PRIO_HIGH)
            writer.put(Message("DATA", "plugin_foo", low_body, "foo", 0))
            writer.put(Message("DATA", "plugin_bar", normal_body, "foo", 1))
            writer.put(Message("DATA", "plugin_baz", high_body, "foo", 2))

        inject_messages()
        writer.send()
        self.assertEqual(client.post.call_count, 1)
        messages = client.post.call_args[0][0]['messages']

        self.assertEqual(len(messages), 4)
        # First two messages (of equal priority) arrive in order or insertion
        self.assertEqual(messages[0]['plugin'], 'plugin_fuz')
        self.assertEqual(messages[1]['plugin'], 'plugin_baz')
        # Remaining messages arrive in priority order
        self.assertEqual(messages[2]['plugin'], 'plugin_bar')
        self.assertEqual(messages[3]['plugin'], 'plugin_foo')
