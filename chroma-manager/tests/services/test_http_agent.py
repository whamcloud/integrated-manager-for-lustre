
"""
Tests for the inter-service interactions that occur through the lifetime of an agent device_plugin session
"""

from chroma_core.lib.util import chroma_settings

settings = chroma_settings()

from Queue import Empty
import json
import time
import datetime
import requests
from django.db import transaction

from chroma_core.models import ManagedHost, HostContactAlert
from chroma_core.services import _amqp_connection
from chroma_core.services.http_agent.host_state import HostState, HostStatePoller

from tests.services.supervisor_test_case import SupervisorTestCase

# The amount of time we allow rabbitmq to forward a message (including
# the time it takes the receiving process to wake up and handle it)
# Should be very very quick.
RABBITMQ_GRACE_PERIOD = 1


class TestHttpAgent(SupervisorTestCase):
    """
    Test that when everything is running and healthy, a session can be established and messages within
    it go back and forth
    """
    SERVICES = ['http_agent']
    PORTS = [settings.HTTP_AGENT_PORT]
    PLUGIN = 'test_messaging'
    RX_QUEUE_NAME = "agent_test_messaging_rx"
    TX_QUEUE_NAME = 'agent_tx'
    CLIENT_NAME = 'myserver'
    HEADERS = {
        "Accept": "application/json",
        "Content-type": "application/json",
        "X-SSL-Client-Name": 'myserver'}
    URL = "http://localhost:%s/agent/message/" % settings.HTTP_AGENT_PORT

    def __init__(self, *args, **kwargs):
        super(TestHttpAgent, self).__init__(*args, **kwargs)
        self.client_start_time = datetime.datetime.now().isoformat()
        self.server_boot_time = datetime.datetime.now().isoformat()
        self.get_params = {'server_boot_time': self.server_boot_time, 'client_start_time': self.client_start_time}

    def assertResponseOk(self, response):
        self.assertTrue(response.ok, "%s: %s" % (response.status_code, response.content))

    def _flush_queue(self, queue):
        with _amqp_connection() as conn:
            conn.SimpleQueue(queue).consumer.purge()

    def _open_session(self, expect_termination = None, expect_initial = True):
        """
        :param expect_termination: Whether to expect the server to have state for an existing
                                   session replaced by this session
        :param expect_initial: Whether to expect the server to behave as if this is the first
                               request it has received after starting
        :return: session ID string
        """
        message = {
            'fqdn': self.CLIENT_NAME,
            'type': 'SESSION_CREATE_REQUEST',
            'plugin': self.PLUGIN,
            'session_id': None,
            'session_seq': None,
            'body': None
        }

        # Send a session create request on the RX channel
        response = requests.post(self.URL, data = json.dumps({'messages': [message]}), headers = self.HEADERS)
        self.assertResponseOk(response)

        # Read from the TX channel
        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        self.assertResponseOk(response)

        if expect_initial:
            # On the first connection from a host that this http_agent hasn't
            # seen before, http_agent sends a TERMINATE_ALL
            # and then the SESSION_CREATE_RESPONSE
            self.assertEqual(len(response.json()['messages']), 2)
            response_message = response.json()['messages'][1]
        else:
            # Should be one SESSION_CREATE_RESPONSE message back to the agent
            self.assertEqual(len(response.json()['messages']), 1)
            response_message = response.json()['messages'][0]
        self.assertEqual(response_message['type'], 'SESSION_CREATE_RESPONSE')
        self.assertEqual(response_message['plugin'], self.PLUGIN)
        self.assertEqual(response_message['session_seq'], None)
        self.assertEqual(response_message['body'], None)
        session_id = response_message['session_id']

        if expect_termination is not None:
            # Should be a SESSION_TERMINATE for the session we are replacing
            message = self._receive_one_amqp()
            self.assertDictEqual(message, {
                'fqdn': self.CLIENT_NAME,
                'type': 'SESSION_TERMINATE',
                'plugin': self.PLUGIN,
                'session_seq': None,
                'session_id': expect_termination,
                'body': None
            })

        # Should be one SESSION_CREATE message to AMQP with a matching session ID
        message = self._receive_one_amqp()
        self.assertDictEqual(message, {
            'fqdn': self.CLIENT_NAME,
            'type': 'SESSION_CREATE',
            'plugin': self.PLUGIN,
            'session_seq': None,
            'session_id': session_id,
            'body': None
        })

        return session_id

    def _receive_one_amqp(self):
        TIMEOUT = RABBITMQ_GRACE_PERIOD
        # Data message should be forwarded to AMQP
        with _amqp_connection() as conn:
            q = conn.SimpleQueue(self.RX_QUEUE_NAME, serializer = 'json')
            try:
                message = q.get(timeout = TIMEOUT)
                message.ack()
            except Empty:
                raise AssertionError("No message received in %s seconds from queue %s" % (TIMEOUT, self.RX_QUEUE_NAME))
            else:
                return message.decode()

    def _send_one_amqp(self, message):
        with _amqp_connection() as conn:
            q = conn.SimpleQueue(self.TX_QUEUE_NAME, serializer = 'json')
            q.put(message)

    def setUp(self):
        super(TestHttpAgent, self).setUp()

        self._flush_queue(self.RX_QUEUE_NAME)
        self._flush_queue(self.TX_QUEUE_NAME)

        if not ManagedHost.objects.filter(fqdn = self.CLIENT_NAME).count():
            self.host = ManagedHost.objects.create(
                fqdn = self.CLIENT_NAME,
                nodename = self.CLIENT_NAME,
                address = self.CLIENT_NAME
            )

    def tearDown(self):
        super(TestHttpAgent, self).tearDown()
        try:
            with transaction.commit_manually():
                transaction.commit()
            host = ManagedHost.objects.get(fqdn = self.CLIENT_NAME)
            HostContactAlert.filter_by_item(host).delete()
            host.mark_deleted()
        except ManagedHost.DoesNotExist:
            pass

    def test_reopen_session(self):
        """Test that opening a new session that supercedes a previous one
        is accepted, and results in a session termination message for
        the previous session being sent to AMQP"""
        first_session_id = self._open_session()
        second_session_id = self._open_session(expect_termination = first_session_id, expect_initial = False)
        self.assertNotEqual(first_session_id, second_session_id)

    def test_message_rx(self):
        """Test that messages POSTed to http_agent are forwarded to AMQP"""

        self.maxDiff = 1000
        session_id = self._open_session()

        # Send a data message in our new session
        sent_data_message = {
            'fqdn': self.CLIENT_NAME,
            'type': 'DATA',
            'plugin': 'test_messaging',
            'session_id': session_id,
            'session_seq': 0,
            'body': None
        }
        response = requests.post(self.URL, data = json.dumps({'messages': [sent_data_message]}), headers = self.HEADERS)
        self.assertResponseOk(response)

        forwarded_data_message = self._receive_one_amqp()

        self.assertDictEqual(sent_data_message, forwarded_data_message)

    def test_message_tx(self):
        """Test that messages put to an AMQP queue are forwared to the agent"""
        session_id = self._open_session()

        sent_fresh_message = {
            'fqdn': self.CLIENT_NAME,
            'type': 'DATA',
            'plugin': 'test_messaging',
            'session_id': session_id,
            'session_seq': 0,
            'body': None
        }
        self._send_one_amqp(sent_fresh_message)

        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        self.assertResponseOk(response)
        forwarded_messages = response.json()['messages']
        self.assertEqual(len(forwarded_messages), 1)
        self.assertEqual(forwarded_messages[0], sent_fresh_message)

    def test_tx_stale_on_get(self):
        """Test that messages not forwarded to the agent when their session ID has
        been superceded (messages which are fresh when sent to the http agent
        but stale by the time the agent comes and GETs them).
        """

        stale_session_id = self._open_session()

        sent_stale_message = {
            'fqdn': self.CLIENT_NAME,
            'type': 'DATA',
            'plugin': 'test_messaging',
            'session_id': stale_session_id,
            'session_seq': 0,
            'body': None
        }
        self._send_one_amqp(sent_stale_message)

        # We need http_agent to definitely have received that stale message
        # by the time we open our fresh session for this test to be distinct
        time.sleep(RABBITMQ_GRACE_PERIOD)
        fresh_session_id = self._open_session(expect_termination = stale_session_id, expect_initial = False)

        sent_fresh_message = {
            'fqdn': self.CLIENT_NAME,
            'type': 'DATA',
            'plugin': 'test_messaging',
            'session_id': fresh_session_id,
            'session_seq': 0,
            'body': None
        }
        self._send_one_amqp(sent_fresh_message)

        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        self.assertResponseOk(response)
        forwarded_messages = response.json()['messages']
        self.assertEqual(len(forwarded_messages), 1)
        self.assertEqual(forwarded_messages[0], sent_fresh_message)

    def test_restart(self):
        """Test that when the http_agent service restarts, agents
        which GET are sent a message to terminate any sessions
        they have open"""

        first_session_id = self._open_session()

        self.restart('http_agent')

        # If we try to continue our session, it will tell us to terminate
        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        self.assertResponseOk(response)
        forwarded_messages = response.json()['messages']
        self.assertEqual(len(forwarded_messages), 1)
        self.assertDictEqual(forwarded_messages[0], {
            'fqdn': self.CLIENT_NAME,
            'type': 'SESSION_TERMINATE_ALL',
            'plugin': None,
            'session_seq': None,
            'session_id': None,
            'body': None
            })

        # And we can open a new session which will get a new ID
        second_session_id = self._open_session(expect_initial = False)
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

        # Should be one SESSION_CREATE message to AMQP with a matching session ID
        message = self._receive_one_amqp()
        self.assertDictEqual(message, {
            'fqdn': self.CLIENT_NAME,
            'type': 'SESSION_TERMINATE',
            'plugin': self.PLUGIN,
            'session_seq': None,
            'session_id': session_id,
            'body': None
        })

        with transaction.commit_manually():
            transaction.commit()
        alerts = HostContactAlert.filter_by_item(self.host)
        self.assertEqual(alerts.count(), 1)
