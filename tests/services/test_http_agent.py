"""
Tests for the inter-service interactions that occur through the lifetime of an agent device_plugin session
"""
import json
import httplib
import urllib
import urlparse

from chroma_core.lib.util import chroma_settings

settings = chroma_settings()

from Queue import Empty
import time

from chroma_core.models import ManagedHost, HostContactAlert, ClientCertificate
from chroma_core.services import _amqp_connection
from chroma_core.services.http_agent.host_state import HostState, HostStatePoller
from chroma_core.services.http_agent import HttpAgentRpc

from tests.services.systemd_test_case import SystemdTestCase
from tests.services.agent_http_client import AgentHttpClient

# The amount of time we allow rabbitmq to forward a message (including
# the time it takes the receiving process to wake up and handle it)
# Should be very very quick.
RABBITMQ_GRACE_PERIOD = 1


class BackgroundGet(httplib.HTTPConnection):
    "Send request immediately.  Get response on demand."

    def __init__(self, test_case):
        parts = urlparse.urlparse(test_case.URL)
        httplib.HTTPConnection.__init__(self, parts.netloc)
        params = {"client_start_time": test_case.client_start_time, "server_boot_time": test_case.server_boot_time}
        self.request("GET", parts.path + "?" + urllib.urlencode(params), headers=test_case.headers)

    @property
    def messages(self):
        response = self.getresponse()
        assert response.status == httplib.OK
        return json.load(response)["messages"]


class TestHttpAgent(SystemdTestCase, AgentHttpClient):
    """
    Test that when everything is running and healthy, a session can be established and messages within
    it go back and forth
    """

    SERVICES = ["emf-http-agent"]
    PLUGIN = "test_messaging"
    RX_QUEUE_NAME = "agent_test_messaging_rx"
    TX_QUEUE_NAME = "agent_tx"

    def __init__(self, *args, **kwargs):
        SystemdTestCase.__init__(self, *args, **kwargs)
        AgentHttpClient.__init__(self)

    def _open_session(self, expect_termination=None, expect_initial=True):
        """
        :param expect_termination: Whether to expect the server to have state for an existing
                                   session replaced by this session
        :param expect_initial: Whether to expect the server to behave as if this is the first
                               request it has received after starting
        :return: session ID string
        """
        message = {
            "fqdn": self.CLIENT_NAME,
            "type": "SESSION_CREATE_REQUEST",
            "plugin": self.PLUGIN,
            "session_id": None,
            "session_seq": None,
            "body": None,
        }

        # Send a session create request on the RX channel
        response = self._post([message])
        self.assertResponseOk(response)

        # Read from the TX channel
        response = self._get()
        self.assertResponseOk(response)

        if expect_initial:
            # On the first connection from a host that this http_agent hasn't
            # seen before, http_agent sends a TERMINATE_ALL
            # and then the SESSION_CREATE_RESPONSE
            self.assertEqual(len(response.json()["messages"]), 2)
            response_message = response.json()["messages"][1]
        else:
            # Should be one SESSION_CREATE_RESPONSE message back to the agent
            self.assertEqual(len(response.json()["messages"]), 1)
            response_message = response.json()["messages"][0]
        self.assertEqual(response_message["type"], "SESSION_CREATE_RESPONSE")
        self.assertEqual(response_message["plugin"], self.PLUGIN)
        self.assertEqual(response_message["session_seq"], None)
        self.assertEqual(response_message["body"], None)
        session_id = response_message["session_id"]

        if expect_termination is not None:
            # Should be a SESSION_TERMINATE for the session we are replacing
            message = self._receive_one_amqp()
            self.assertDictEqual(
                message,
                {
                    "fqdn": self.CLIENT_NAME,
                    "type": "SESSION_TERMINATE",
                    "plugin": self.PLUGIN,
                    "session_seq": None,
                    "session_id": expect_termination,
                    "body": None,
                },
            )

        # Should be one SESSION_CREATE message to AMQP with a matching session ID
        message = self._receive_one_amqp()
        self.assertDictEqual(
            message,
            {
                "fqdn": self.CLIENT_NAME,
                "type": "SESSION_CREATE",
                "plugin": self.PLUGIN,
                "session_seq": None,
                "session_id": session_id,
                "body": None,
            },
        )

        return session_id

    def _flush_queue(self, queue):
        with _amqp_connection() as conn:
            conn.SimpleQueue(queue, exchange_opts={"durable": False}, queue_opts={"durable": False}).consumer.purge()

    def _receive_one_amqp(self):
        TIMEOUT = RABBITMQ_GRACE_PERIOD
        # Data message should be forwarded to AMQP
        with _amqp_connection() as conn:
            q = conn.SimpleQueue(
                self.RX_QUEUE_NAME, serializer="json", exchange_opts={"durable": False}, queue_opts={"durable": False}
            )
            try:
                message = q.get(timeout=TIMEOUT)
                message.ack()
            except Empty:
                raise AssertionError("No message received in %s seconds from queue %s" % (TIMEOUT, self.RX_QUEUE_NAME))
            else:
                return message.decode()

    def _send_one_amqp(self, message):
        with _amqp_connection() as conn:
            q = conn.SimpleQueue(
                self.TX_QUEUE_NAME, serializer="json", exchange_opts={"durable": False}, queue_opts={"durable": False}
            )
            q.put(message)

    def setUp(self):
        if not ManagedHost.objects.filter(fqdn=self.CLIENT_NAME).count():
            self.host = ManagedHost.objects.create(
                fqdn=self.CLIENT_NAME, nodename=self.CLIENT_NAME, address=self.CLIENT_NAME
            )
            ClientCertificate.objects.create(host=self.host, serial=self.CLIENT_CERT_SERIAL)

        super(TestHttpAgent, self).setUp()

        self._flush_queue(self.RX_QUEUE_NAME)
        self._flush_queue(self.TX_QUEUE_NAME)

    def tearDown(self):
        super(TestHttpAgent, self).tearDown()

        try:
            host = ManagedHost.objects.get(fqdn=self.CLIENT_NAME)
            HostContactAlert.filter_by_item(host).delete()
            host.mark_deleted()
        except ManagedHost.DoesNotExist:
            pass

    def test_reopen_session(self):
        """Test that opening a new session that supercedes a previous one
        is accepted, and results in a session termination message for
        the previous session being sent to AMQP"""
        first_session_id = self._open_session()
        second_session_id = self._open_session(expect_termination=first_session_id, expect_initial=False)
        self.assertNotEqual(first_session_id, second_session_id)

    def test_message_rx(self):
        """Test that messages POSTed to http_agent are forwarded to AMQP"""

        self.maxDiff = 1000
        session_id = self._open_session()

        # Send a data message in our new session
        sent_data_message = {
            "fqdn": self.CLIENT_NAME,
            "type": "DATA",
            "plugin": "test_messaging",
            "session_id": session_id,
            "session_seq": 0,
            "body": None,
        }
        response = self._post([sent_data_message])
        self.assertResponseOk(response)

        forwarded_data_message = self._receive_one_amqp()

        self.assertDictEqual(sent_data_message, forwarded_data_message)

    def test_message_tx(self):
        """Test that messages put to an AMQP queue are forwared to the agent"""
        session_id = self._open_session()

        sent_fresh_message = {
            "fqdn": self.CLIENT_NAME,
            "type": "DATA",
            "plugin": "test_messaging",
            "session_id": session_id,
            "session_seq": 0,
            "body": None,
        }
        self._send_one_amqp(sent_fresh_message)

        response = self._get()
        self.assertResponseOk(response)
        forwarded_messages = response.json()["messages"]
        self.assertEqual(len(forwarded_messages), 1)
        self.assertEqual(forwarded_messages[0], sent_fresh_message)

    def test_zombie_get(self):
        """Test that when an agent is hard-killed, or its host restarts (such that
        an outstanding GET connection is not torn down), then when the agent 'comes back
        to life' and opens another GET connection, TX messages make it to the new agent
        rather than going into a black hole on the zombie connection.  This scenario
        is HYD-2063"""

        # Pretend to be the first agent instance
        zombie_session_id = self._open_session()
        # Start doing a GET
        zombie = BackgroundGet(self)

        # Leaving that GET open, imagine the agent now gets killed hard
        self._mock_restart()

        # The agent restarts, now I pretend to be the second agent instance
        healthy_session_id = self._open_session(expect_termination=zombie_session_id)
        healthy = BackgroundGet(self)

        # In the HYD-2063 case, there are now two HTTP GET handlers subscribed to the
        # TX messages for our host, so when we send a message, it might go to the healthy
        # one, or it might go to the unhealthy one.  Send ten messages to give a decent
        # chance that if they all go to the right place then there isn't a bug.
        message_count = 10
        for i in range(0, message_count):
            sent_fresh_message = {
                "fqdn": self.CLIENT_NAME,
                "type": "DATA",
                "plugin": "test_messaging",
                "session_id": healthy_session_id,
                "session_seq": i,
                "body": None,
            }
            self._send_one_amqp(sent_fresh_message)
            # Avoid bunching up the messages so that they have a decent
            # chance of being sent to different handlers if there are
            # multiple handelrs in flight
            time.sleep(0.1)

        self.assertListEqual(zombie.messages, [])
        healthy_messages = len(healthy.messages)
        for attempt in range(9):
            messages = BackgroundGet(self).messages
            healthy_messages += len(messages)
            if healthy_messages >= message_count or not messages:
                break  # retrieved them all, or a GET timeout

        self.assertEqual(healthy_messages, message_count)

    def test_tx_stale_on_get(self):
        """Test that messages not forwarded to the agent when their session ID has
        been superceded (messages which are fresh when sent to the http agent
        but stale by the time the agent comes and GETs them).
        """

        stale_session_id = self._open_session()

        sent_stale_message = {
            "fqdn": self.CLIENT_NAME,
            "type": "DATA",
            "plugin": "test_messaging",
            "session_id": stale_session_id,
            "session_seq": 0,
            "body": None,
        }
        self._send_one_amqp(sent_stale_message)

        # We need http_agent to definitely have received that stale message
        # by the time we open our fresh session for this test to be distinct
        time.sleep(RABBITMQ_GRACE_PERIOD)
        fresh_session_id = self._open_session(expect_termination=stale_session_id, expect_initial=False)

        sent_fresh_message = {
            "fqdn": self.CLIENT_NAME,
            "type": "DATA",
            "plugin": "test_messaging",
            "session_id": fresh_session_id,
            "session_seq": 0,
            "body": None,
        }
        self._send_one_amqp(sent_fresh_message)

        response = self._get()
        self.assertResponseOk(response)
        forwarded_messages = response.json()["messages"]
        self.assertEqual(len(forwarded_messages), 1)
        self.assertEqual(forwarded_messages[0], sent_fresh_message)

    def test_restart(self):
        """Test that when the http_agent service restarts, agents
        which GET are sent a message to terminate any sessions
        they have open"""

        first_session_id = self._open_session()

        self.restart("emf-http-agent")

        # If we try to continue our session, it will tell us to terminate
        response = self._get()
        self.assertResponseOk(response)
        forwarded_messages = response.json()["messages"]
        self.assertEqual(len(forwarded_messages), 1)
        self.assertDictEqual(
            forwarded_messages[0],
            {
                "fqdn": self.CLIENT_NAME,
                "type": "SESSION_TERMINATE_ALL",
                "plugin": None,
                "session_seq": None,
                "session_id": None,
                "body": None,
            },
        )

        # And we can open a new session which will get a new ID
        second_session_id = self._open_session(expect_initial=False)
        self.assertNotEqual(first_session_id, second_session_id)

    def test_timeout(self):
        """Test that when a session is established, then left idle
        for the timeout period, the http_agent service emits
        a termination message on the RX channel."""
        session_id = self._open_session()

        # No alert to begin with
        alerts = HostContactAlert.filter_by_item(self.host)
        self.assertEqual(alerts.count(), 0)

        time.sleep(HostState.CONTACT_TIMEOUT + HostStatePoller.POLL_INTERVAL + RABBITMQ_GRACE_PERIOD)

        # Should be one SESSION_TERMINATE message to AMQP with a matching session ID
        message = self._receive_one_amqp()
        self.assertDictEqual(
            message,
            {
                "fqdn": self.CLIENT_NAME,
                "type": "SESSION_TERMINATE",
                "plugin": self.PLUGIN,
                "session_seq": None,
                "session_id": session_id,
                "body": None,
            },
        )

        alerts = HostContactAlert.filter_by_item(self.host)
        self.assertEqual(alerts.count(), 1)

        # Should be a message waiting for the agent telling it that its session was terminated
        # (timing out doesn't mean the agent is gone, it could just be experiencing network difficulties)
        # What's more, the agent doesn't necessarily *know* that it had network difficulties, e.g. if it
        # just got real slow and waited too long between GETs.
        # This has to cut both ways to be reliable:
        # * We have to tell the agent that we thought it went away, by sending a TERMINATE for sessions
        # * If the agent finds that a GET fails then it has to assume that we might have put session
        #   messages in that GET, and terminate all its sessions in case one of those GET messages
        #   was really a TERMINATE
        response = self._get()
        self.assertResponseOk(response)
        forwarded_messages = response.json()["messages"]
        self.assertEqual(len(forwarded_messages), 1)
        self.assertDictEqual(
            forwarded_messages[0],
            {
                "fqdn": self.CLIENT_NAME,
                "type": "SESSION_TERMINATE",
                "plugin": self.PLUGIN,
                "session_seq": None,
                "session_id": None,
                "body": None,
            },
        )

    def test_revoked_cert(self):
        """Check that I'm bounced if my certificate is revoked"""

        # Initially should be able to to operations like open a session
        self._open_session()
        HttpAgentRpc().remove_host(self.host.fqdn)

        # After revokation any access should be bounced
        response = self._post([])
        self.assertEqual(response.status_code, 403)
        response = self._get()
        self.assertEqual(response.status_code, 403)
