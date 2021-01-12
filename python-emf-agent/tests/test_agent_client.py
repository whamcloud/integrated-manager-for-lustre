import logging
import time
import json
import datetime
import mock

import unittest

from chroma_agent.agent_client import (
    HttpWriter,
    Message,
    HttpReader,
    SessionTable,
    HttpError,
)
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import (
    PRIO_LOW,
    DevicePluginMessage,
    PRIO_NORMAL,
    PRIO_HIGH,
)
from emf_common.lib.date_time import EMFDateTime


class TestHttpWriter(unittest.TestCase):
    def test_message_callback(self):
        """Test that when a callback is included in a Message(), it is invoked
        after the message is sent"""

        client = mock.Mock()
        client._fqdn = "test_server"
        client.device_plugins = mock.Mock()
        client.device_plugins.get_plugins = mock.Mock(return_value=["test_plugin"])
        client.boot_time = EMFDateTime.utcnow()
        client.start_time = EMFDateTime.utcnow()

        callback = mock.Mock()

        # Disable poll() so that it's not trying to set up sessions, just doing passthrough of messages
        with mock.patch("chroma_agent.agent_client.HttpWriter.poll"):
            try:
                writer = HttpWriter(client)
                writer.start()

                message = Message(
                    "DATA",
                    "test_plugin",
                    {"key1": "val1"},
                    "session_foo",
                    666,
                    callback=callback,
                )
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
                            raise RuntimeError(
                                "Timeout waiting for .post() and callback (%s %s)"
                                % (client.post.call_count, callback.call_count)
                            )

                # Should have sent back the result
                self.assertEqual(client.post.call_count, 1)
                self.assertDictEqual(
                    client.post.call_args[0][0],
                    {
                        "messages": [message.dump(client._fqdn)],
                        "server_boot_time": client.boot_time.isoformat() + "Z",
                        "client_start_time": client.start_time.isoformat() + "Z",
                    },
                )

                # Should have invoked the callback
                self.assertEqual(callback.call_count, 1)
            finally:
                writer.stop()
                writer.join()

    def test_priorities(self):
        """
        Test that messages are consumed for POST based on the priority of the payload (data plane), or at the highest
        priority if no payload (control plane)
        """

        client = mock.Mock()
        client._fqdn = "test_server"
        client.boot_time = EMFDateTime.utcnow()
        client.start_time = EMFDateTime.utcnow()

        writer = HttpWriter(client)

        def inject_messages(*args, **kwargs):
            # A control plane message
            writer.put(Message("SESSION_CREATE_REQUEST", "plugin_fuz", None, None, None))

            low_body = DevicePluginMessage("low", PRIO_LOW)
            normal_body = DevicePluginMessage("normal", PRIO_NORMAL)
            high_body = DevicePluginMessage("high", PRIO_HIGH)
            writer.put(Message("DATA", "plugin_foo", low_body, "foo", 0))
            writer.put(Message("DATA", "plugin_bar", normal_body, "foo", 1))
            writer.put(Message("DATA", "plugin_baz", high_body, "foo", 2))

        inject_messages()
        writer.send()
        self.assertEqual(client.post.call_count, 1)
        messages = client.post.call_args[0][0]["messages"]

        self.assertEqual(len(messages), 4)
        # First two messages (of equal priority) arrive in order or insertion
        self.assertEqual(messages[0]["plugin"], "plugin_fuz")
        self.assertEqual(messages[1]["plugin"], "plugin_baz")
        # Remaining messages arrive in priority order
        self.assertEqual(messages[2]["plugin"], "plugin_bar")
        self.assertEqual(messages[3]["plugin"], "plugin_foo")

    def test_session_backoff(self):
        """Test that when messages to the manager are being dropped due to POST failure,
        sending SESSION_CREATE_REQUEST messages has a power-of-two backoff wait"""
        client = mock.Mock()
        client._fqdn = "test_server"
        client.boot_time = EMFDateTime.utcnow()
        client.start_time = EMFDateTime.utcnow()

        writer = client.writer = HttpWriter(client)
        reader = client.reader = HttpReader(client)

        daemon_log.setLevel(logging.DEBUG)

        TestPlugin = mock.Mock()

        mock_plugin_instance = mock.Mock()
        mock_plugin_instance.start_session = mock.Mock(return_value={"foo": "bar"})
        client.device_plugins.get = mock.Mock(return_value=lambda _: mock_plugin_instance)
        client.device_plugins.get_plugins = mock.Mock(return_value={"test_plugin": TestPlugin})
        client.sessions = SessionTable(client)

        client.post = mock.Mock(side_effect=HttpError())

        # Pick an arbitrary time to use as a base for simulated waits
        t_0 = datetime.datetime.now()

        old_datetime = datetime.datetime
        try:

            def expect_message_at(t):
                datetime.datetime.now = mock.Mock(return_value=t - datetime.timedelta(seconds=0.1))
                writer.poll("test_plugin")
                self.assertEqual(writer._messages.qsize(), 0)

                datetime.datetime.now = mock.Mock(return_value=t + datetime.timedelta(seconds=0.1))
                writer.poll("test_plugin")
                self.assertEqual(writer._messages.qsize(), 1)

            datetime.datetime = mock.Mock()
            datetime.datetime.now = mock.Mock(return_value=t_0)

            # Stage 1: failing to POST, backing off
            # =====================================

            # Poll should put some session creation messages
            writer.poll("test_plugin")
            self.assertEqual(writer._messages.qsize(), 1)
            # Another poll immediately after shouldn't add any messages (MIN_SESSION_BACKOFF hasn't passed)
            writer.poll("test_plugin")
            self.assertEqual(writer._messages.qsize(), 1)

            # Send should consume the messages, and they go to nowhere because the POST fails
            writer.send()
            client.post.assert_called_once()
            self.assertEqual(len(client.post.call_args[0][0]["messages"]), 1)

            # First time boundary: where the first repeat should happen
            from chroma_agent.agent_client import MIN_SESSION_BACKOFF

            t_1 = t_0 + MIN_SESSION_BACKOFF

            expect_message_at(t_1)

            # Have another crack at sending, it should fail and empty the queue
            writer.send()
            self.assertTrue(writer._messages.empty())

            # Second time boundary: where the second repeat should happen
            t_2 = t_1 + MIN_SESSION_BACKOFF * 2
            expect_message_at(t_2)

            # Stage 2: success in POST, session creation
            # ==========================================

            # This time we'll let the message go through, and a session to begin.
            client.post = mock.Mock()
            writer.send()

            # HttpReader receives a response from the manager, and should reset the backoff counters.
            reader._handle_messages(
                [
                    {
                        "type": "SESSION_CREATE_RESPONSE",
                        "plugin": "test_plugin",
                        "session_id": "id_foo",
                        "session_seq": 0,
                        "body": {},
                    }
                ]
            )
            self.assertEqual(len(client.sessions._sessions), 1)
            session = client.sessions.get("test_plugin")

            # State 3: POSTs start failing again, see delay again
            # ===================================================

            # Break the POST link again
            client.post = mock.Mock(side_effect=HttpError())

            # Poll will get a DATA message from initial_scan
            session.initial_scan = mock.Mock(return_value={"foo": "bar"})
            writer.poll("test_plugin")
            session.initial_scan.assert_called_once()
            self.assertFalse(writer._messages.empty())

            # Send will fail to send it, and as a result destroy the session
            writer.send()
            self.assertTrue(writer._messages.empty())
            self.assertEqual(len(client.sessions._sessions), 0)

            # Move to some point beyond the first backoff cycle
            t_3 = t_0 + datetime.timedelta(seconds=60)
            datetime.datetime.now = mock.Mock(return_value=t_3)

            writer.poll("test_plugin")
            self.assertEqual(writer._messages.qsize(), 1)
            writer.poll("test_plugin")
            self.assertEqual(writer._messages.qsize(), 1)
            writer.send()
            self.assertEqual(writer._messages.qsize(), 0)

            # Check the backoff time has gone back to MIN_SESSION_BACKOFF
            t_4 = t_3 + MIN_SESSION_BACKOFF
            expect_message_at(t_4)
        finally:
            datetime.datetime = old_datetime

    def test_oversized_messages(self):
        """
        Test that oversized messages are dropped and the session is terminated
        """
        # Monkey-patch this setting to a lower limit to make testing easier
        MAX_BYTES_PER_POST = 1024
        from chroma_agent.agent_client import (
            MAX_BYTES_PER_POST as LARGE_MAX_BYTES_PER_POST,
        )

        def set_post_limit(size):
            import chroma_agent.agent_client

            chroma_agent.agent_client.MAX_BYTES_PER_POST = size

        self.addCleanup(set_post_limit, LARGE_MAX_BYTES_PER_POST)
        set_post_limit(MAX_BYTES_PER_POST)

        client = mock.Mock()
        client._fqdn = "test_server"
        client.boot_time = EMFDateTime.utcnow()
        client.start_time = EMFDateTime.utcnow()

        writer = HttpWriter(client)

        def fake_post(envelope):
            if len(json.dumps(envelope)) > MAX_BYTES_PER_POST:
                daemon_log.info("fake_post(): rejecting oversized message")
                raise HttpError()

        client.post = mock.Mock(side_effect=fake_post)
        TestPlugin = mock.Mock()

        mock_plugin_instance = mock.Mock()
        mock_plugin_instance.start_session = mock.Mock(return_value={"foo": "bar"})
        client.device_plugins.get = mock.Mock(return_value=lambda _: mock_plugin_instance)
        client.device_plugins.get_plugins = mock.Mock(return_value={"test_plugin": TestPlugin})
        client.sessions = SessionTable(client)

        daemon_log.setLevel(logging.DEBUG)

        import string
        from random import choice

        oversized_string = "".join(choice(string.printable) for i in range(MAX_BYTES_PER_POST))

        # There should be one message to set up the session
        writer.poll("test_plugin")
        self.assertTrue(writer.send())
        self.assertEqual(client.post.call_count, 1)
        messages = client.post.call_args[0][0]["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "SESSION_CREATE_REQUEST")
        # Pretend we got a SESSION_CREATE_RESPONSE
        client.sessions.create("test_plugin", "id_foo")
        self.assertEqual(len(client.sessions._sessions), 1)

        # Inject a normal and an oversized message
        normal_body = DevicePluginMessage("normal", PRIO_NORMAL)
        oversized_body = DevicePluginMessage(oversized_string, PRIO_NORMAL)
        writer.put(Message("DATA", "test_plugin", normal_body, "id_foo", 0))
        writer.put(Message("DATA", "test_plugin", oversized_body, "id_foo", 1))

        # Only the normal message should get through
        self.assertTrue(writer.send())
        self.assertEqual(client.post.call_count, 2)
        messages = client.post.call_args[0][0]["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "DATA")

        # The oversized message should be dropped and the session
        # terminated
        self.assertFalse(writer.send())
        self.assertEqual(client.post.call_count, 3)
        self.assertEqual(len(client.sessions._sessions), 0)

        # However, we should eventually get a new session for the
        # offending plugin
        writer.poll("test_plugin")
        self.assertTrue(writer.send())
        self.assertEqual(client.post.call_count, 4)
        messages = client.post.call_args[0][0]["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "SESSION_CREATE_REQUEST")


class TestHttpReader(unittest.TestCase):
    def test_data_message(self):
        client = mock.Mock()
        client._fqdn = "test_server"

        client.sessions = SessionTable(client)
        session = mock.Mock()
        session.id = "foo_id"
        client.sessions._sessions["test_plugin"] = session

        reader = HttpReader(client)
        reader._handle_messages(
            [
                {
                    "type": "DATA",
                    "plugin": "test_plugin",
                    "session_id": "foo_id",
                    "session_seq": None,
                    "fqdn": "test_server",
                    "body": {"body": "foo"},
                }
            ]
        )

        session.receive_message.assertCalledOnceWith({"body": "foo"})

    def test_data_message_exception(self):
        """Test that if receive_message raises an exception, the session is terminated"""

        client = mock.Mock()
        client._fqdn = "test_server"

        client.sessions = SessionTable(client)
        session = mock.Mock()
        session.id = "foo_id"
        client.sessions._sessions["test_plugin"] = session

        session.receive_message = mock.Mock(side_effect=RuntimeError())

        reader = HttpReader(client)
        reader._handle_messages(
            [
                {
                    "type": "DATA",
                    "plugin": "test_plugin",
                    "session_id": "foo_id",
                    "session_seq": None,
                    "fqdn": "test_server",
                    "body": {"body": "foo"},
                }
            ]
        )

        # Should have called our teardown method
        session.teardown.assertCalledOnce()
        # Should have removed the session
        self.assertNotIn("test_plugin", client.sessions._sessions)
