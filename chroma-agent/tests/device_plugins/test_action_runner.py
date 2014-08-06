import time

from chroma_agent.chroma_common.lib import shell
from chroma_agent.device_plugins.action_runner import ActionRunnerPlugin, CallbackAfterResponse
from chroma_agent.plugin_manager import ActionPluginManager, DevicePlugin
from django.utils import unittest
import mock


ACTION_ONE_RETVAL = 'action_one_return'


subprocesses = {
    ('subprocess_one', 'subprocess_one_arg'): lambda: (0, 'subprocess_one_stdout', 'subprocess_one_stderr'),
    ('subprocess_two', 'subprocess_two_arg'): lambda: (-1, 'subprocess_two_stdout', 'subprocess_two_stderr')
}


def action_one(arg1):
    """An action which invokes subprocess_one"""

    assert arg1 == "arg1_test"
    stdout = shell.try_run(['subprocess_one', 'subprocess_one_arg'])
    assert stdout == 'subprocess_one_stdout'
    return ACTION_ONE_RETVAL


def action_two(arg1):
    """An action which invokes subprocess_one and subprocess_two"""

    assert arg1 == "arg1_test"
    stdout = shell.try_run(['subprocess_one', 'subprocess_one_arg'])
    assert stdout == 'subprocess_one_stdout'
    shell.try_run(['subprocess_two', 'subprocess_two_arg'])
    return ACTION_ONE_RETVAL


def action_three():
    """An action which runs for a long time unless interrupted"""

    shell.try_run(['sleep', '10000'])
    raise AssertionError("subprocess three should last forever!")


def action_four():
    """An action which raises an CallbackAfterResponse"""

    def action_four_callback():
        return 'action_four_called_back'

    raise CallbackAfterResponse('result', action_four_callback)

ACTIONS = [action_one, action_two, action_three, action_four]


class ActionTestCase(unittest.TestCase):
    MOCK_SUBPROCESSES = None

    def setUp(self):
        # Register some testing actions
        self.action_plugins = ActionPluginManager()
        for action in ACTIONS:
            self.action_plugins.commands[action.__name__] = action

        # Intercept messages sent
        self.old_send_message = DevicePlugin.send_message
        DevicePlugin.send_message = mock.Mock()

        # Intercept subprocess invocations
        if self.MOCK_SUBPROCESSES:
            self.old_run = shell._run
            shell._run = mock.Mock(side_effect = lambda args: self.MOCK_SUBPROCESSES[tuple(args)]())

    def tearDown(self):
        for action in ACTIONS:
            del ActionPluginManager.commands[action.__name__]

        if self.MOCK_SUBPROCESSES:
            shell._run = self.old_run


class TestActionPluginManager(ActionTestCase):
    """
    Test running actions directly as a precursor to testing running them
    via ActionRunner.
    """
    MOCK_SUBPROCESSES = subprocesses

    def test_run_direct_success(self):
        """
        Test that we can run an action directly using ActionPluginManager (as the
        CLI would)
        """
        result = ActionPluginManager().run('action_one', {'arg1': "arg1_test"})
        self.assertEqual(result, ACTION_ONE_RETVAL)

    def test_run_direct_failure(self):
        """
        Test that ActionPluginManager.run re-raises exceptions
        """
        with self.assertRaises(AssertionError):
            ActionPluginManager().run('action_one', {'arg1': "the_wrong_thing"})


class ActionRunnerPluginTestCase(ActionTestCase):
    def setUp(self):
        super(ActionRunnerPluginTestCase, self).setUp()

        # counter for generating deterministic action IDs
        self._id_counter = 0

        # Intercept messages sent
        self.old_send_message = DevicePlugin.send_message
        DevicePlugin.send_message = mock.Mock()

        # ActionRunner tries to do acces self._session._client.action_plugins
        # to get at ActionPluginManager
        self.client = mock.Mock()
        self.client.action_plugins = self.action_plugins
        self.session = mock.Mock()
        self.session._client = self.client

        self.action_runner = ActionRunnerPlugin(self.session)

    def tearDown(self):
        super(ActionRunnerPluginTestCase, self).tearDown()

        DevicePlugin.send_message = self.old_send_message

    def _run_action(self, action, args):
        """
        Invoke an action by pretending that the manager sent a message
        """
        id = "%s" % self._id_counter
        self._id_counter += 1
        self.action_runner.on_message({
            'type': 'ACTION_START',
            'id': id,
            'action': action,
            'args': args
        })
        return id

    def _get_responses(self, count):
        # The ActionRunnerPlugin will run the action in a thread, and call send_message when
        # it completes
        # NB: when polling a Mock() from another thread, we rely on call_count being set before call_args_list: it
        # is safe to poll on call_args_list and then assume call_count is set, but not vice versa.
        TIMEOUT = 2
        i = 0
        while True:
            if len(DevicePlugin.send_message.call_args_list) >= count:
                break
            else:
                time.sleep(1)
                i += 1

            if i > TIMEOUT:
                raise AssertionError("Timed out after %ss waiting for %s responses (got %s)" % (TIMEOUT, count, DevicePlugin.send_message.call_count))

        self.assertEqual(DevicePlugin.send_message.call_count, count)
        return [args[0][0] for args in DevicePlugin.send_message.call_args_list]


class TestActionRunnerPlugin(ActionRunnerPluginTestCase):

    MOCK_SUBPROCESSES = subprocesses

    def test_run_action_runner(self):
        """
        Test that we can run an action in a thread using ActionRunnerPlugin (as
        the manager would via the HTTPS agent comms)
        """

        id = self._run_action('action_one', {'arg1': 'arg1_test'})
        response = self._get_responses(1)[0]
        self.assertDictEqual(response, {
            'type': 'ACTION_COMPLETE',
            'id': id,
            'result': ACTION_ONE_RETVAL,
            'exception': None,
            'subprocesses': [{
                'args': ['subprocess_one', 'subprocess_one_arg'],
                'stdout': 'subprocess_one_stdout',
                'stderr': 'subprocess_one_stderr',
                'rc': 0
            }]
        })

    def test_run_action_runner_error(self):
        """
        Test running an action which experiences an error in a subprocess
        """

        id = self._run_action('action_two', {'arg1': 'arg1_test'})
        response = self._get_responses(1)[0]
        self.assertEqual(response['id'], id)
        self.assertIsNone(response['result'])
        self.assertIsNotNone(response['exception'])
        self.assertListEqual(response['subprocesses'], [
            {
                'args': ['subprocess_one', 'subprocess_one_arg'],
                'stdout': 'subprocess_one_stdout',
                'stderr': 'subprocess_one_stderr',
                'rc': 0
            },
            {
                'args': ['subprocess_two', 'subprocess_two_arg'],
                'stdout': 'subprocess_two_stdout',
                'stderr': 'subprocess_two_stderr',
                'rc': -1
            },
            ])

    def test_two_actions(self):
        """
        Test running two actions, checking that their 'subprocesses' output is separated
        """
        id_1 = self._run_action('action_one', {'arg1': 'arg1_test'})
        id_2 = self._run_action('action_two', {'arg1': 'arg1_test'})
        responses = self._get_responses(2)
        response_1 = [r for r in responses if r['id'] == id_1][0]
        response_2 = [r for r in responses if r['id'] == id_2][0]

        self.assertDictEqual(response_1, {
            'type': 'ACTION_COMPLETE',
            'id': id_1,
            'result': ACTION_ONE_RETVAL,
            'exception': None,
            'subprocesses': [{
                             'args': ['subprocess_one', 'subprocess_one_arg'],
                             'stdout': 'subprocess_one_stdout',
                             'stderr': 'subprocess_one_stderr',
                             'rc': 0
                         }]
        })

        self.assertEqual(response_2['id'], id_2)
        self.assertIsNone(response_2['result'])
        self.assertIsNotNone(response_2['exception'])
        self.assertListEqual(response_2['subprocesses'], [
            {
                'args': ['subprocess_one', 'subprocess_one_arg'],
                'stdout': 'subprocess_one_stdout',
                'stderr': 'subprocess_one_stderr',
                'rc': 0
            },
            {
                'args': ['subprocess_two', 'subprocess_two_arg'],
                'stdout': 'subprocess_two_stdout',
                'stderr': 'subprocess_two_stderr',
                'rc': -1
            },
            ])


class TestActionRunnerPluginCancellation(ActionRunnerPluginTestCase):
    def test_teardown(self):
        """Test that tearing down ActionRunnerPlugin interrupts execution of
        subprocesses.  This is what happens on a session termination."""

        # The action for this test has to be a bit subtle: we can't just override _run
        # because we need its behaviour

        self._run_action('action_three', {})
        # Now that something is in flight, try tearing down
        self.action_runner.teardown()
        # The main test here is that we actually return rather than blocking indefinitely

        # No messages should have been sent during teardown
        self.assertEqual(DevicePlugin.send_message.call_count, 0)

    def test_cancellation(self):
        """Test that sending a cancellation message for a running action interrupts
        execution of subprocesses.  This is what happens on a particular action
        being cancelled from the manager"""
        id = self._run_action('action_three', {})

        # Grab the internal thread so that we can check it completes
        thread = self.action_runner._running_actions[id]

        self.action_runner.on_message({
            'type': 'ACTION_CANCEL',
            'id': id,
            'action': None,
            'args': None
        })

        # The thread should have stopped running
        thread.join(2.0)
        self.assertFalse(thread.is_alive())

        # No messages should have been sent during cancellation
        self.assertEqual(DevicePlugin.send_message.call_count, 0)


class TestCallbackAfterResponse(ActionRunnerPluginTestCase):
    def _get_response_and_callback(self):
        # The ActionRunnerPlugin will run the action in a thread, and call send_message when
        # it completes
        # NB: when polling a Mock() from another thread, we rely on call_count being set before call_args_list: it
        # is safe to poll on call_args_list and then assume call_count is set, but not vice versa.

        TIMEOUT = 2
        i = 0
        while True:
            if DevicePlugin.send_message.call_args is not None:
                break
            else:
                time.sleep(1)
                i += 1

            if i > TIMEOUT:
                raise AssertionError("Timed out after %ss waiting for responses (got %s)" % (TIMEOUT, DevicePlugin.send_message.call_count))

        self.assertEqual(DevicePlugin.send_message.call_count, 1)
        return DevicePlugin.send_message.call_args[0][0], DevicePlugin.send_message.call_args[0][1]

    def test_passthrough(self):
        """Test that when an action raises an CallbackAfterResponse, the
        ActionRunnerPlugin tags the callback onto the Message that it sends
        onwards"""

        self._run_action('action_four', {})

        response, callback = self._get_response_and_callback()
        self.assertEqual(callback(), 'action_four_called_back')
