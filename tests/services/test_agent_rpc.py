from chroma_core.lib.util import chroma_settings

settings = chroma_settings()

import django

django.setup()

import time

from collections import namedtuple
from tests.services.systemd_test_case import SystemdTestCase
from tests.services.agent_http_client import AgentHttpClient
from emf_common.lib import util
from emf_common.lib.date_time import EMFDateTime
from chroma_core.services.http_agent import HostStatePoller
from chroma_core.services.http_agent.host_state import HostState
from chroma_core.services.job_scheduler.agent_rpc import AgentRpcMessenger
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.models import ManagedHost
from chroma_core.models import HostContactAlert
from chroma_core.models import Command
from chroma_core.models import LNetConfiguration
from chroma_core.models import ClientCertificate
from chroma_core.models import AlertEmail
from chroma_core.models import ServerProfile


RABBITMQ_GRACE_PERIOD = 1
RABBITMQ_LONGWAIT_PERIOD = 360


class TestAgentRpc(SystemdTestCase, AgentHttpClient):
    """
    This class tests the AgentRpc functionality.  This class starts the job_scheduler
    service because that is where AgentRpc lives, but is not intended to test the other
    functionality in JobScheduler.
    """

    SERVICES = ["emf-http-agent", "emf-job-scheduler"]
    PLUGIN = AgentRpcMessenger.PLUGIN_NAME

    def __init__(self, *args, **kwargs):
        SystemdTestCase.__init__(self, *args, **kwargs)
        AgentHttpClient.__init__(self)

    def _open_sessions(self, expect_initial=True, expect_reopen=False):
        message = {
            "fqdn": self.CLIENT_NAME,
            "type": "SESSION_CREATE_REQUEST",
            "plugin": self.PLUGIN,
            "session_id": None,
            "session_seq": None,
            "body": None,
        }

        # On the first connection from a host that this http_agent hasn't seen before, http_agent sends a TERMINATE_ALL
        # In that case, send a session-less DATA request expecting a TERMINATE
        # In addition to flushing the TERMINATE_ALL, this gives the job_scheduler time to reset all sessions
        if expect_initial:
            response = self._post([dict(message, type="DATA")])
            self.assertResponseOk(response)
            messages = self._receive_messages(2)
            self.assertEqual([m["type"] for m in messages], ["SESSION_TERMINATE_ALL", "SESSION_TERMINATE"])

        # Send a session create request on the RX channel
        response = self._post([message])
        self.assertResponseOk(response)

        # Read from the TX channel
        (create_response,) = self._receive_messages()
        self.assertEqual(create_response["type"], "SESSION_CREATE_RESPONSE")
        self.assertEqual(create_response["plugin"], self.PLUGIN)
        self.assertEqual(create_response["session_seq"], None)
        self.assertEqual(create_response["body"], None)
        return create_response["session_id"]

    def setUp(self):
        if not ManagedHost.objects.filter(fqdn=self.CLIENT_NAME).count():
            if not ServerProfile.objects.filter(name="TestAgentRpcProfile").count():
                server_profile = ServerProfile.objects.create(
                    name="TestAgentRpcProfile",
                    ui_name="Profile created to TestAgentRpc can work",
                    managed=True,
                    worker=False,
                    ntp=True,
                    corosync=True,
                    corosync2=False,
                )
            else:
                server_profile = ServerProfile.objects.get(name="TestAgentRpcProfile")

            self.host = ManagedHost.objects.create(
                fqdn=self.CLIENT_NAME,
                nodename=self.CLIENT_NAME,
                address=self.CLIENT_NAME,
                state="lnet_down",
                state_modified_at=EMFDateTime.utcnow(),
                server_profile=server_profile,
            )
            LNetConfiguration.objects.create(host=self.host, state="lnet_down")
            ClientCertificate.objects.create(host=self.host, serial=self.CLIENT_CERT_SERIAL)
        else:
            self.host = ManagedHost.objects.get(fqdn=self.CLIENT_NAME)

        super(TestAgentRpc, self).setUp()

    def tearDown(self):
        super(TestAgentRpc, self).tearDown()
        try:
            host = ManagedHost.objects.get(fqdn=self.CLIENT_NAME)
            for host_contact_alert in HostContactAlert.filter_by_item(host):
                AlertEmail.objects.filter(alerts__in=[host_contact_alert]).delete()
                host_contact_alert.delete()
            host.mark_deleted()
        except ManagedHost.DoesNotExist:
            pass

    def test_restart(self):
        """
        When restarting the job_scheduler service, an RPC to http_agent should be issued to
        cancel all open sessions for the action_runner plugin.
        """

        self._open_sessions()
        self.restart("emf-job-scheduler")

        # Allow the message to filter through
        time.sleep(RABBITMQ_GRACE_PERIOD)

        # Agent should see a termination (this will prompt it to request a new session)
        response_message = self._receive_messages(1)[0]
        self.assertEqual(response_message["type"], "SESSION_TERMINATE")
        self.assertEqual(response_message["plugin"], self.PLUGIN)
        self.assertEqual(response_message["session_seq"], None)
        self.assertEqual(response_message["session_id"], None)
        self.assertEqual(response_message["body"], None)

    ActionsRequested = namedtuple("ActionsRequested", ["command_id", "actions"])

    def _request_action(self, state="lnet_up"):
        # Start a job which should generate an action
        command_id = JobSchedulerClient.command_set_state(
            [(self.host.lnet_configuration.content_type.natural_key(), self.host.lnet_configuration.id, state)], "Test"
        )
        command = self._get_command(command_id)
        self.assertEqual(len(command.jobs.all()), 1)
        self.last_action = time.time()

        # This have to be hardcoded and kept up to date, a bit crappy, but at least they are in one
        # place and asserts when it doesn't know what to do.
        # This is basically describing the messages that we expect to receive when a command is sent.
        # We can then receive and validate each message as it arrives.
        if state == "lnet_up":
            actions = ["start_lnet", "device_plugin"]  # It will do start_lnet, followed by 1 request for data.
        elif state == "lnet_down":
            actions = ["stop_lnet", "device_plugin"]  # It will do stop_lnet, followed by 1 request for data.
        else:
            raise AssertionError("Unknown state '%s' requested for _request_action" % state)

        return self.ActionsRequested(command_id, actions)

    def _handle_action_receive(self, session_id, action):
        # Listen and wait for the action
        (action_rpc_request,) = self._receive_messages()
        msg = "elapsed {0}".format(time.time() - self.last_action)
        self.assertEqual(action_rpc_request["type"], "DATA", msg)
        self.assertEqual(action_rpc_request["plugin"], self.PLUGIN)
        self.assertEqual(action_rpc_request["session_seq"], None)
        self.assertEqual(action_rpc_request["session_id"], session_id)
        if action_rpc_request["body"]["action"] != action:
            pass
        self.assertEqual(action_rpc_request["body"]["action"], action)

        return action_rpc_request["body"]

    def _handle_action_respond(self, session_id, rpc_request_body):
        # Send it a success response
        message = {
            "fqdn": self.CLIENT_NAME,
            "type": "DATA",
            "plugin": self.PLUGIN,
            "session_id": session_id,
            "session_seq": 1,
            "body": {
                "type": "ACTION_COMPLETE",
                "id": rpc_request_body["id"],
                "exception": None,
                "result": None,
                "subprocesses": [],
            },
        }

        # Now we are going to simulate some alternative replys, this are simple and hardcoded but
        # but we do have an assert for cases we don't understand and this is not trying to be a simulator
        action = rpc_request_body["action"]
        if action in ["start_lnet", "stop_lnet"]:
            pass
        elif action == "device_plugin":
            assert rpc_request_body["args"]["plugin"] in ["linux_network", "linux"]
            message["body"]["exception"] = "No data provided by test scripts - this is intentional"
        else:
            raise AssertionError("_handle_action_respond can't respond to %s" % action)

        action_data_response = self._post([message])
        self.assertResponseOk(action_data_response)

    def _handle_action(self, session_id, actions):
        for action in actions:
            rpc_request_body = self._handle_action_receive(session_id, action)
            response = self._handle_action_respond(session_id, rpc_request_body)

        return response

    def _get_command(self, command_id):
        return Command.objects.get(pk=command_id)

    def _wait_for_command(self, command_id, timeout):
        """Wait for at least timeout"""
        for _ in util.wait(timeout):
            command = self._get_command(command_id)
            if command.complete:
                return command

        for _ in util.wait(RABBITMQ_LONGWAIT_PERIOD):
            command = self._get_command(command_id)
            if command.complete:
                break

        if command.complete:
            raise AssertionError(
                "Command didn't complete after %s seconds but did after %s seconds"
                % (timeout, RABBITMQ_LONGWAIT_PERIOD)
            )
        else:
            raise AssertionError("Command didn't complete even after %s seconds" % RABBITMQ_LONGWAIT_PERIOD)

    def test_run_action(self):
        # Prepare to receive actions
        agent_session_id = self._open_sessions()

        request_action = self._request_action()

        self._handle_action(agent_session_id, request_action.actions)

        command = self._wait_for_command(request_action.command_id, RABBITMQ_GRACE_PERIOD)
        self.assertFalse(command.errored)
        self.assertFalse(command.cancelled)

    def test_run_action_no_session(self):
        """
        Before starting the agent, try to run an agent_rpc.  See that it is marked as errored after the startup timeout.
        """

        # Start a job which should generate an action
        request_action = self._request_action()

        command = self._wait_for_command(request_action.command_id, AgentRpcMessenger.SESSION_WAIT_TIMEOUT * 2)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_run_action_delayed_session(self):
        """
        Before starting the agent, try to run an agent_rpc.  Start the agent within the startup timeout and see that the operation succeeds.
        """

        # Start a job which should generate an action
        request_action = self._request_action()

        time.sleep(AgentRpcMessenger.SESSION_WAIT_TIMEOUT / 2)

        session_id = self._open_sessions()
        self._handle_action(session_id, request_action.actions)

        command = self._wait_for_command(request_action.command_id, AgentRpcMessenger.SESSION_WAIT_TIMEOUT * 2)
        self.assertFalse(command.errored)
        self.assertFalse(command.cancelled)

    def test_stop_while_in_flight(self):
        """
        While an agent rpc is in flight, stop the job_scheduler: check it stops cleanly and leaves all jobs marked as cancelled
        """

        agent_session_id = self._open_sessions()

        first_request_action = self._request_action()

        # Create another job which will be enqueued
        queued_request_action = self._request_action("lnet_down")

        # Start 'running' the action
        self._handle_action_receive(agent_session_id, first_request_action.actions[0])

        # Clean stop
        self.stop("emf-job-scheduler")

        # Running command should have its AgentRpc errored
        running_command = self._get_command(first_request_action.command_id)
        self.assertTrue(running_command.complete)
        self.assertTrue(running_command.errored)

        # Waiting command should have been marked cancelled
        enqueued_command = self._get_command(queued_request_action.command_id)
        self.assertTrue(enqueued_command.complete)
        self.assertTrue(enqueued_command.cancelled)
        self.assertFalse(enqueued_command.errored)

        # Start it up again
        self.start("emf-job-scheduler")

        # It should have the http_agent service cancel its sessions
        response_message = self._receive_messages(1)[0]
        self.assertEqual(response_message["type"], "SESSION_TERMINATE")
        self.assertEqual(response_message["plugin"], self.PLUGIN)
        self.assertEqual(response_message["session_seq"], None)
        self.assertEqual(response_message["session_id"], None)
        self.assertEqual(response_message["body"], None)

    def test_restart_http_agent_while_in_flight(self):
        """While and agent rpc is in flight, restart the http_agent service, check that the command is errored"""
        agent_session_id = self._open_sessions()

        request_action = self._request_action()

        # Start 'running' the action
        self._handle_action_receive(agent_session_id, request_action.actions[0])

        # Clean stop
        self.restart("emf-http-agent")

        # The agent should be told to terminate all
        response_message = self._receive_messages(1)[0]
        self.assertEqual(response_message["type"], "SESSION_TERMINATE_ALL")
        self.assertEqual(response_message["plugin"], None)
        self.assertEqual(response_message["session_seq"], None)
        self.assertEqual(response_message["session_id"], None)
        self.assertEqual(response_message["body"], None)

        # The job_scheduler should have been messaged a termination of the session, and
        # in response to that should have errored the commands
        command = self._wait_for_command(request_action.command_id, 5)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_restart_agent_while_in_flight(self):
        """While an agent rpc is in flight, restart the agent: check that the command is errored"""

        agent_session_id = self._open_sessions()

        request_action = self._request_action()

        # Start 'running' the action
        self._handle_action_receive(agent_session_id, request_action.actions[0])

        # Simulate an agent restart
        self._open_sessions(expect_initial=False, expect_reopen=True)

        # The job_scheduler should have been messaged a termination of the session, and
        # in response to that should have errored the commands
        command = self._wait_for_command(request_action.command_id, 5)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_timeout_while_in_flight(self):
        """
        While an agent rpc is in flight, allow the agent comms to time out: check that the
        command is marked as cancelled
        """
        agent_session_id = self._open_sessions()

        request_action = self._request_action()

        # Start 'running' the action
        self._handle_action_receive(agent_session_id, request_action.actions[0])

        # Allow session to time out
        time.sleep(HostState.CONTACT_TIMEOUT + HostStatePoller.POLL_INTERVAL + RABBITMQ_GRACE_PERIOD)

        # The job_scheduler should have been messaged a termination of the session, and
        # in response to that should have errored the commands
        command = self._wait_for_command(request_action.command_id, 5)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_timeout_while_idle(self):
        """
        While a session is idle, allow it to time out, and check that a subsequent action is failed.
        """
        self._open_sessions()

        # Allow session to time out
        time.sleep(HostState.CONTACT_TIMEOUT + HostStatePoller.POLL_INTERVAL + RABBITMQ_GRACE_PERIOD)

        request_action = self._request_action()

        # The job_scheduler should have been messaged a termination of the session, and
        # in response to that should have errored the commands
        command = self._wait_for_command(request_action.command_id, AgentRpcMessenger.SESSION_WAIT_TIMEOUT * 2)
        self.assertTrue(command.errored)
        self.assertFalse(command.cancelled)

    def test_cancellation(self):
        """
        While an agent rpc is in flight, check that issuing a cancellation on the manager
        results in a cancel message being sent to the agent, and the command completing
        promptly on the manager.
        """
        agent_session_id = self._open_sessions()
        request_action = self._request_action()
        rpc_request = self._handle_action_receive(agent_session_id, request_action.actions[0])

        command = self._get_command(request_action.command_id)
        for job in command.jobs.all():
            JobSchedulerClient.cancel_job(job.id)

        # The command should get cancelled promptly
        command = self._wait_for_command(command.id, RABBITMQ_GRACE_PERIOD)
        self.assertTrue(command.cancelled)
        self.assertFalse(command.errored)

        # A cancellation for the agent rpc should have been sent to the agent
        cancellation_message = self._receive_messages(1)[0]
        self.assertDictEqual(
            cancellation_message["body"],
            {"type": "ACTION_CANCEL", "id": rpc_request["id"], "action": None, "args": None},
        )

    def test_HYD_2389(self):
        "Initial test to check if HYD-2389 only reproduces on first run."
        agent_session_id = self._open_sessions()
        request_action = self._request_action()
        self._handle_action_receive(agent_session_id, request_action.actions[0])
