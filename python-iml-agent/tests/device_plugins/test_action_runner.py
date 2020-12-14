import time
from collections import namedtuple
import threading
import mock

import unittest

from chroma_agent.lib.shell import AgentShell
from chroma_agent.device_plugins.action_runner import (
    ActionRunnerPlugin,
    CallbackAfterResponse,
)
from chroma_agent.plugin_manager import ActionPluginManager, DevicePlugin
from chroma_agent.agent_client import AgentDaemonContext

ACTION_ONE_NO_CONTEXT_RETVAL = "action_one_no_context_return"
ACTION_ONE_WITH_CONTEXT_RETVAL = "action_one_with_context_return"
ACTION_TWO_RETVAL = "action_two_return"


subprocesses = {
    ("subprocess_one", "subprocess_one_arg"): lambda: AgentShell.RunResult(
        0, "subprocess_one_stdout", "subprocess_one_stderr", False
    ),
    ("subprocess_two", "subprocess_two_arg"): lambda: AgentShell.RunResult(
        -1, "subprocess_two_stdout", "subprocess_two_stderr", False
    ),
}


def action_one_no_context(arg1):
    """An action which invokes subprocess_one"""

    assert arg1 == "arg1_test"
    stdout = AgentShell.try_run(["subprocess_one", "subprocess_one_arg"])
    assert stdout == "subprocess_one_stdout"
    return ACTION_ONE_NO_CONTEXT_RETVAL


def action_one_with_context(agent_daemon_context, arg1):
    """An action which invokes subprocess_one"""

    assert isinstance(agent_daemon_context, AgentDaemonContext)
    assert arg1 == "arg1_test"
    stdout = AgentShell.try_run(["subprocess_one", "subprocess_one_arg"])
    assert stdout == "subprocess_one_stdout"
    return ACTION_ONE_WITH_CONTEXT_RETVAL


def action_two(arg1):
    """An action which invokes subprocess_one and subprocess_two"""

    assert arg1 == "arg2_test"
    stdout = AgentShell.try_run(["subprocess_one", "subprocess_one_arg"])
    assert stdout == "subprocess_one_stdout"
    AgentShell.try_run(["subprocess_two", "subprocess_two_arg"])
    return ACTION_TWO_RETVAL


def action_three():
    """An action which runs for a long time unless interrupted"""

    AgentShell.try_run(["sleep", "10000"])
    raise AssertionError("subprocess three should last forever!")


def action_four():
    """An action which raises an CallbackAfterResponse"""

    def action_four_callback():
        return "action_four_called_back"

    raise CallbackAfterResponse("result", action_four_callback)


ACTIONS = [
    action_one_no_context,
    action_one_with_context,
    action_two,
    action_three,
    action_four,
]


class ActionTestCase(unittest.TestCase):
    MOCK_SUBPROCESSES = None

    SendMessageParams = namedtuple("SendMessageParams", ["body", "callback"])

    def mock_send_message(self, body, callback=None):
        self.mock_send_message_lock.acquire()
        self.mock_send_message_call_args_list.append(self.SendMessageParams(body, callback))
        self.mock_send_message_call_count += 1
        self.mock_send_message_lock.release()

    def mock_run(self, args, logger, result_store, timeout, shell=False):
        return self.MOCK_SUBPROCESSES[tuple(args)]()

    def setUp(self):
        # Register some testing actions
        self.action_plugins = ActionPluginManager()
        for action in ACTIONS:
            self.action_plugins.commands[action.__name__] = action

        # Intercept messages sent with a thread safe mock
        mock.patch(
            "chroma_agent.plugin_manager.DevicePlugin.send_message",
            self.mock_send_message,
        ).start()
        self.mock_send_message_lock = threading.Lock()
        self.mock_send_message_call_count = 0
        self.mock_send_message_call_args_list = []

        # Intercept subprocess invocations
        if self.MOCK_SUBPROCESSES:
            mock.patch("iml_common.lib.shell.BaseShell._run", self.mock_run).start()

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        for action in ACTIONS:
            del ActionPluginManager.commands[action.__name__]


class TestActionPluginManager(ActionTestCase):
    """
    Test running actions directly as a precursor to testing running them
    via ActionRunner.
    """

    MOCK_SUBPROCESSES = subprocesses

    def test_run_direct_success(self):
        """
        Test that we can run an action directly using ActionPluginManager as the
        CLI would.
        """
        result = ActionPluginManager().run("action_one_no_context", None, {"arg1": "arg1_test"})
        self.assertEqual(result, ACTION_ONE_NO_CONTEXT_RETVAL)

    def test_run_direct_failure(self):
        """
        Test that ActionPluginManager.run re-raises exceptions
        """
        with self.assertRaises(AssertionError):
            ActionPluginManager().run("action_one_no_context", None, {"arg1": "the_wrong_thing"})

    def test_run_direct_success_with_context(self):
        """
        Test that we can run an action using ActionPluginManager as the
        daemon would.
        """
        result = ActionPluginManager().run("action_one_with_context", AgentDaemonContext([]), {"arg1": "arg1_test"})
        self.assertEqual(result, ACTION_ONE_WITH_CONTEXT_RETVAL)


class ActionRunnerPluginTestCase(ActionTestCase):
    def setUp(self):
        super(ActionRunnerPluginTestCase, self).setUp()

        # counter for generating deterministic action IDs
        self._id_counter = 0

        # ActionRunner tries to do access self._session._client.action_plugins
        # to get at ActionPluginManager
        self.client = mock.Mock()
        self.client.action_plugins = self.action_plugins
        self.session = mock.Mock()
        self.session._client = self.client

        self.action_runner = ActionRunnerPlugin(self.session)

    def _run_action(self, action, args):
        """
        Invoke an action by pretending that the manager sent a message
        """
        id = "%s" % self._id_counter
        self._id_counter += 1
        self.action_runner.on_message({"type": "ACTION_START", "id": id, "action": action, "args": args})
        return id

    def _get_responses(self, count):
        # The ActionRunnerPlugin will run the action in a thread, and call send_message when it completes
        TIMEOUT = 2
        i = 0
        while self.mock_send_message_call_count < count:
            time.sleep(1)
            i += 1

            if i > TIMEOUT:
                raise AssertionError(
                    "Timed out after %ss waiting for %s responses (got %s)"
                    % (TIMEOUT, count, DevicePlugin.send_message.call_count)
                )

        self.assertEqual(self.mock_send_message_call_count, count)
        return [args.body for args in self.mock_send_message_call_args_list]


class TestActionRunnerPlugin(ActionRunnerPluginTestCase):

    MOCK_SUBPROCESSES = subprocesses

    def test_run_action_runner(self):
        """
        Test that we can run an action in a thread using ActionRunnerPlugin (as
        the manager would via the HTTPS agent comms)
        """

        x = self._run_action("action_one_no_context", {"arg1": "arg1_test"})
        response = self._get_responses(1)[0]
        self.assertDictEqual(
            response,
            {
                "type": "ACTION_COMPLETE",
                "id": x,
                "result": ACTION_ONE_NO_CONTEXT_RETVAL,
                "exception": None,
                "subprocesses": [
                    {
                        "args": ["subprocess_one", "subprocess_one_arg"],
                        "stdout": "subprocess_one_stdout",
                        "stderr": "subprocess_one_stderr",
                        "rc": 0,
                    }
                ],
            },
        )

    def test_run_action_runner_error(self):
        """
        Test running an action which experiences an error in a subprocess
        """

        id = self._run_action("action_two", {"arg1": "arg2_test"})
        response = self._get_responses(1)[0]
        self.assertEqual(response["id"], id)
        self.assertIsNone(response["result"])
        self.assertIsNotNone(response["exception"])
        self.assertListEqual(
            response["subprocesses"],
            [
                {
                    "args": ["subprocess_one", "subprocess_one_arg"],
                    "stdout": "subprocess_one_stdout",
                    "stderr": "subprocess_one_stderr",
                    "rc": 0,
                },
                {
                    "args": ["subprocess_two", "subprocess_two_arg"],
                    "stdout": "subprocess_two_stdout",
                    "stderr": "subprocess_two_stderr",
                    "rc": -1,
                },
            ],
        )

    def test_1000_actions(self):
        """
        Test running 10000 actions, checking that their 'subprocesses' output is separated
        """
        actions = 1000
        ids = {}

        for action in xrange(0, actions):
            if action & 1:
                ids[action] = self._run_action("action_one_no_context", {"arg1": "arg1_test"})
            else:
                ids[action] = self._run_action("action_two", {"arg1": "arg2_test"})

        responses = self._get_responses(actions)

        for action in xrange(0, actions):
            response = next(r for r in responses if r["id"] == ids[action])

            if action & 1:
                self.assertDictEqual(
                    response,
                    {
                        "type": "ACTION_COMPLETE",
                        "id": ids[action],
                        "result": ACTION_ONE_NO_CONTEXT_RETVAL,
                        "exception": None,
                        "subprocesses": [
                            {
                                "args": ["subprocess_one", "subprocess_one_arg"],
                                "stdout": "subprocess_one_stdout",
                                "stderr": "subprocess_one_stderr",
                                "rc": 0,
                            }
                        ],
                    },
                )
            else:
                self.assertIsNone(response["result"])
                self.assertIsNotNone(response["exception"])
                self.assertListEqual(
                    response["subprocesses"],
                    [
                        {
                            "args": ["subprocess_one", "subprocess_one_arg"],
                            "stdout": "subprocess_one_stdout",
                            "stderr": "subprocess_one_stderr",
                            "rc": 0,
                        },
                        {
                            "args": ["subprocess_two", "subprocess_two_arg"],
                            "stdout": "subprocess_two_stdout",
                            "stderr": "subprocess_two_stderr",
                            "rc": -1,
                        },
                    ],
                )


class TestActionRunnerPluginCancellation(ActionRunnerPluginTestCase):
    def test_teardown(self):
        """Test that tearing down ActionRunnerPlugin interrupts execution of
        subprocesses.  This is what happens on a session termination."""

        # The action for this test has to be a bit subtle: we can't just override _run
        # because we need its behaviour

        self._run_action("action_three", {})
        # Now that something is in flight, try tearing down
        self.action_runner.teardown()
        # The main test here is that we actually return rather than blocking indefinitely

        # No messages should have been sent during teardown
        self.assertEqual(self.mock_send_message_call_count, 0)

    def test_cancellation(self):
        """Test that sending a cancellation message for a running action interrupts
        execution of subprocesses.  This is what happens on a particular action
        being cancelled from the manager"""
        id = self._run_action("action_three", {})

        # Grab the internal thread so that we can check it completes
        thread = self.action_runner._running_actions[id]

        self.action_runner.on_message({"type": "ACTION_CANCEL", "id": id, "action": None, "args": None})

        # The thread should have stopped running
        thread.join(2.0)
        self.assertFalse(thread.is_alive())

        # No messages should have been sent during cancellation
        self.assertEqual(self.mock_send_message_call_count, 0)


class TestCallbackAfterResponse(ActionRunnerPluginTestCase):
    def _get_response_and_callback(self):
        # The ActionRunnerPlugin will run the action in a thread, and call send_message when
        # it completes
        # NB: when polling a Mock() from another thread, we rely on call_count being set before call_args_list: it
        # is safe to poll on call_args_list and then assume call_count is set, but not vice versa.

        TIMEOUT = 2
        i = 0
        while self.mock_send_message_call_count == 0:
            time.sleep(1)
            i += 1

            if i > TIMEOUT:
                raise AssertionError(
                    "Timed out after %ss waiting for responses (got %s)"
                    % (TIMEOUT, DevicePlugin.send_message.call_count)
                )

        self.assertEqual(self.mock_send_message_call_count, 1)
        return self.mock_send_message_call_args_list[0]

    def test_passthrough(self):
        """Test that when an action raises an CallbackAfterResponse, the
        ActionRunnerPlugin tags the callback onto the Message that it sends
        onwards"""

        self._run_action("action_four", {})

        response_and_callback = self._get_response_and_callback()
        self.assertEqual(response_and_callback.callback(), "action_four_called_back")
