

from chroma_core.lib.util import chroma_settings
settings = chroma_settings()

import dateutil
import json
import datetime
import time
import requests
from django.db import transaction

from tests.services.supervisor_test_case import SupervisorTestCase
from chroma_core.services.http_agent import HostStatePoller
from chroma_core.services.http_agent.host_state import HostState
from chroma_core.services.job_scheduler import agent_rpc
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.models import ManagedHost, HostContactAlert, Command

RABBITMQ_GRACE_PERIOD = 1


class TestAgentRpc(SupervisorTestCase):
    """
    This class tests the AgentRpc functionality.  This class starts the job_scheduler
    service because that is where AgentRpc lives, but is not intended to test the other
    functionality in JobScheduler.
    """
    SERVICES = ['http_agent', 'job_scheduler']
    PORTS = [settings.HTTP_AGENT_PORT]

    CLIENT_NAME = 'myserver'
    PLUGIN = agent_rpc.ACTION_MANAGER_PLUGIN_NAME
    URL = "http://localhost:%s/agent/message/" % settings.HTTP_AGENT_PORT
    HEADERS = {
        "Accept": "application/json",
        "Content-type": "application/json",
        "X-SSL-Client-Name": 'myserver'}

    def __init__(self, *args, **kwargs):
        super(TestAgentRpc, self).__init__(*args, **kwargs)
        self.client_start_time = datetime.datetime.now().isoformat()
        self.server_boot_time = datetime.datetime.now().isoformat()
        self.get_params = {'server_boot_time': self.server_boot_time, 'client_start_time': self.client_start_time}

    def _open_sessions(self, expect_initial = True, expect_reopen = False):
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

        expected_count = 1
        if expect_initial:
            # On the first connection from a host that this http_agent hasn't
            # seen before, http_agent sends a TERMINATE_ALL
            # and then the SESSION_CREATE_RESPONSE
            expected_count += 1

        self.assertEqual(len(response.json()['messages']), expected_count)

        create_response = response.json()['messages'][-1]
        self.assertEqual(create_response['type'], 'SESSION_CREATE_RESPONSE')
        self.assertEqual(create_response['plugin'], self.PLUGIN)
        self.assertEqual(create_response['session_seq'], None)
        self.assertEqual(create_response['body'], None)
        session_id = create_response['session_id']

        return session_id

    def setUp(self):
        super(TestAgentRpc, self).setUp()

        if not ManagedHost.objects.filter(fqdn = self.CLIENT_NAME).count():
            self.host = ManagedHost.objects.create(
                fqdn = self.CLIENT_NAME,
                nodename = self.CLIENT_NAME,
                address = self.CLIENT_NAME,
                state = 'lnet_down',
                state_modified_at = datetime.datetime.now(tz = dateutil.tz.tzutc())
            )
        else:
            self.host = ManagedHost.objects.get(fqdn = self.CLIENT_NAME)

    def tearDown(self):
        super(TestAgentRpc, self).tearDown()
        try:
            with transaction.commit_manually():
                transaction.commit()
            host = ManagedHost.objects.get(fqdn = self.CLIENT_NAME)
            HostContactAlert.filter_by_item(host).delete()
            host.mark_deleted()
        except ManagedHost.DoesNotExist:
            pass

    def test_restart(self):
        """
        When restarting the job_scheduler service, an RPC to http_agent should be issued to
        cancel all open sessions for the action_runner plugin.
        """

        self._open_sessions()
        self.restart('job_scheduler')

        # Allow the message to filter through
        time.sleep(RABBITMQ_GRACE_PERIOD)

        # Agent should see a termination (this will prompt it to request a new session)
        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        self.assertResponseOk(response)
        self.assertEqual(len(response.json()['messages']), 1)
        response_message = response.json()['messages'][0]
        self.assertEqual(response_message['type'], 'SESSION_TERMINATE')
        self.assertEqual(response_message['plugin'], self.PLUGIN)
        self.assertEqual(response_message['session_seq'], None)
        self.assertEqual(response_message['session_id'], None)
        self.assertEqual(response_message['body'], None)

    def _request_action(self, state = 'lnet_up'):
        # Start a job which should generate an action
        command_id = JobSchedulerClient.command_set_state([(self.host.content_type.natural_key(), self.host.id, state)], "Test")
        return command_id

    def _receive_agent_messages(self):
        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        return response.json()['messages']

    def _handle_action_receive(self, session_id):
        # Listen for the action
        messages = self._receive_agent_messages()
        self.assertEqual(len(messages), 1)
        action_rpc_request = messages[0]
        self.assertEqual(action_rpc_request['type'], 'DATA')
        self.assertEqual(action_rpc_request['plugin'], self.PLUGIN)
        self.assertEqual(action_rpc_request['session_seq'], None)
        self.assertEqual(action_rpc_request['session_id'], session_id)
        self.assertEqual(action_rpc_request['body']['action'], 'start_lnet')

        return action_rpc_request['body']

    def _handle_action_respond(self, session_id, rpc_request_body):
        # Send it a success response
        success_message = {
            'fqdn': self.CLIENT_NAME,
            'type': 'DATA',
            'plugin': self.PLUGIN,
            'session_id': session_id,
            'session_seq': 1,
            'body': {
                'type': 'ACTION_COMPLETE',
                'id': rpc_request_body['id'],
                'exception': None,
                'result': None,
                'subprocesses': []
            }
        }
        action_data_response = requests.post(self.URL, data = json.dumps({'messages': [success_message]}), headers = self.HEADERS)
        self.assertResponseOk(action_data_response)

    def _handle_action(self, session_id):
        rpc_request_body = self._handle_action_receive(session_id)
        return self._handle_action_respond(session_id, rpc_request_body)

    def _get_command(self, command_id):
        with transaction.commit_manually():
            transaction.commit()
        return Command.objects.get(pk = command_id)

    def _wait_for_command(self, command_id, timeout):
        i = 0
        while i < timeout:
            command = self._get_command(command_id)
            if command.complete:
                return command
            else:
                time.sleep(1)
        raise AssertionError("Command didn't complete")

    def test_run_action(self):
        # Let things start up to avoid our new session getting caught in
        # the service-start cleardown
        time.sleep(5)
        # FIXME: if agents are quick, then their very first session will tend
        # to be killed by the job_scheduler as it starts up (if http_agent
        # and job_scheduler) are started concurrently and http_agent starts
        # listening first.

        # Prepare to receive actions
        agent_session_id = self._open_sessions()

        command_id = self._request_action()

        self._handle_action(agent_session_id)

        command = self._wait_for_command(command_id, RABBITMQ_GRACE_PERIOD)
        self.assertFalse(command.errored)
        self.assertFalse(command.cancelled)

    def test_run_action_no_session(self):
        """
        Before starting the agent, try to run an agent_rpc.  See that it is marked as errored after the startup timeout.
        """

        # Start a job which should generate an action
        command_id = self._request_action()

        command = self._wait_for_command(command_id, agent_rpc.SESSION_WAIT_TIMEOUT * 2)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_run_action_delayed_session(self):
        """
        Before starting the agent, try to run an agent_rpc.  Start the agent within the startup timeout and see that the operation succeeds.
        """

        # Start a job which should generate an action
        command_id = self._request_action()

        time.sleep(agent_rpc.SESSION_WAIT_TIMEOUT / 2)

        session_id = self._open_sessions()
        self._handle_action(session_id)

        command = self._wait_for_command(command_id, agent_rpc.SESSION_WAIT_TIMEOUT * 2)
        self.assertFalse(command.errored)
        self.assertFalse(command.cancelled)

    def test_stop_while_in_flight(self):
        """
        While an agent rpc is in flight, stop the job_scheduler: check it stops cleanly and leaves all jobs marked as cancelled
        """

        agent_session_id = self._open_sessions()

        command_id = self._request_action()

        # Create another job which will be enqueued
        enqueued_command_id = self._request_action('lnet_down')

        # Start 'running' the action
        self._handle_action_receive(agent_session_id)

        # Clean stop
        self.stop('job_scheduler')

        # Running command should have its AgentRpc errored
        running_command = self._get_command(command_id)
        self.assertTrue(running_command.complete)
        self.assertFalse(running_command.cancelled)
        self.assertTrue(running_command.errored)

        # Waiting command should have been marked cancelled
        enqueued_command = self._get_command(enqueued_command_id)
        self.assertTrue(enqueued_command.complete)
        self.assertTrue(enqueued_command.cancelled)
        self.assertFalse(enqueued_command.errored)

        # Start it up again
        self.start('job_scheduler')

        # It should have the http_agent service cancel its sessions
        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        self.assertResponseOk(response)
        self.assertEqual(len(response.json()['messages']), 1)
        response_message = response.json()['messages'][0]
        self.assertEqual(response_message['type'], 'SESSION_TERMINATE')
        self.assertEqual(response_message['plugin'], self.PLUGIN)
        self.assertEqual(response_message['session_seq'], None)
        self.assertEqual(response_message['session_id'], None)
        self.assertEqual(response_message['body'], None)

    def test_restart_http_agent_while_in_flight(self):
        """While and agent rpc is in flight, restart the http_agent service, check that the command is errored"""
        agent_session_id = self._open_sessions()

        command_id = self._request_action()

        # Start 'running' the action
        self._handle_action_receive(agent_session_id)

        # Clean stop
        self.restart('http_agent')

        # The agent should be told to terminate all
        response = requests.get(self.URL, headers = self.HEADERS, params = self.get_params)
        self.assertResponseOk(response)
        self.assertEqual(len(response.json()['messages']), 1)
        response_message = response.json()['messages'][0]
        self.assertEqual(response_message['type'], 'SESSION_TERMINATE_ALL')
        self.assertEqual(response_message['plugin'], None)
        self.assertEqual(response_message['session_seq'], None)
        self.assertEqual(response_message['session_id'], None)
        self.assertEqual(response_message['body'], None)

        # The job_scheduler should have been messaged a termination of the session, and
        # in response to that should have errored the commands
        command = self._wait_for_command(command_id, 5)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_restart_agent_while_in_flight(self):
        """While an agent rpc is in flight, restart the agent: check that the command is errored"""

        agent_session_id = self._open_sessions()

        command_id = self._request_action()

        # Start 'running' the action
        self._handle_action_receive(agent_session_id)

        # Simulate an agent restart
        self._open_sessions(expect_initial = False, expect_reopen = True)

        # The job_scheduler should have been messaged a termination of the session, and
        # in response to that should have errored the commands
        command = self._wait_for_command(command_id, 5)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_timeout_while_in_flight(self):
        """
        While an agent rpc is in flight, allow the agent comms to time out: check that the
        command is marked as cancelled
        """
        agent_session_id = self._open_sessions()

        command_id = self._request_action()

        # Start 'running' the action
        self._handle_action_receive(agent_session_id)

        # Allow session to time out
        time.sleep(HostState.CONTACT_TIMEOUT + HostStatePoller.POLL_INTERVAL + RABBITMQ_GRACE_PERIOD)

        # The job_scheduler should have been messaged a termination of the session, and
        # in response to that should have errored the commands
        command = self._wait_for_command(command_id, 5)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_cancellation(self):
        """
        While an agent rpc is in flight, check that issuing a cancellation on the manager
        results in a cancel message being sent to the agent, and the command completing
        promptly on the manager.
        """
        agent_session_id = self._open_sessions()
        command_id = self._request_action()
        rpc_request = self._handle_action_receive(agent_session_id)

        command = self._get_command(command_id)
        for job in command.jobs.all():
            JobSchedulerClient.cancel_job(job.id)

        # The command should get cancelled promptly
        command = self._wait_for_command(command.id, RABBITMQ_GRACE_PERIOD)
        self.assertTrue(command.cancelled)
        self.assertFalse(command.errored)

        # A cancellation for the agent rpc should have been sent to the agent
        messages = self._receive_agent_messages()
        self.assertEqual(len(messages), 1)
        cancellation_message = messages[0]
        self.assertDictEqual(
            cancellation_message['body'],
            {
                'type': 'ACTION_CANCEL',
                'id': rpc_request['id'],
                'action': None,
                'args': None
            }
        )
