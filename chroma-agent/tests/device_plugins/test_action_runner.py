from chroma_agent import shell
from chroma_agent.device_plugins.action_runner import ActionRunnerPlugin
from chroma_agent.plugin_manager import ActionPluginManager, DevicePlugin
from django.utils import unittest
import mock
import time


ACTION_ONE_RETVAL = 'action_one_return'


subprocesses = {
    ('subprocess_one', 'subprocess_one_arg'): (0, 'subprocess_one_stdout', 'subprocess_one_stderr'),
    ('subprocess_two', 'subprocess_two_arg'): (-1, 'subprocess_two_stdout', 'subprocess_two_stderr'),
}


def action_one(arg1):
    assert arg1 == "arg1_test"
    stdout = shell.try_run(['subprocess_one', 'subprocess_one_arg'])
    assert stdout == 'subprocess_one_stdout'
    return ACTION_ONE_RETVAL


def action_two(arg1):
    assert arg1 == "arg1_test"
    stdout = shell.try_run(['subprocess_one', 'subprocess_one_arg'])
    assert stdout == 'subprocess_one_stdout'
    shell.try_run(['subprocess_two', 'subprocess_two_arg'])
    return ACTION_ONE_RETVAL


class ActionTestCase(unittest.TestCase):
    def setUp(self):
        # Register some testing actions
        self.action_plugins = ActionPluginManager()
        self.action_plugins.commands['action_one'] = action_one
        self.action_plugins.commands['action_two'] = action_two

        # Intercept messages sent
        self.old_send_message = DevicePlugin.send_message
        DevicePlugin.send_message = mock.Mock()

        # Intercept subprocess invocations
        self.old_run = shell._run
        shell._run = mock.Mock(side_effect = lambda args: subprocesses[tuple(args)])

    def tearDown(self):
        del ActionPluginManager.commands['action_one']
        del ActionPluginManager.commands['action_two']
        shell._run = self.old_run


class TestActionPluginManager(ActionTestCase):
    """
    Test running actions directly as a precursor to testing running them
    via ActionRunner.
    """
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


class TestActionRunnerPlugin(ActionTestCase):
    def setUp(self):
        super(TestActionRunnerPlugin, self).setUp()

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
        super(TestActionRunnerPlugin, self).tearDown()

        DevicePlugin.send_message = self.old_send_message

    def _run_action(self, action, args):
        """
        Invoke an action by pretending that the manager sent a message
        """
        id = "%s" % self._id_counter
        self._id_counter += 1
        self.action_runner.on_message({
            'id': id,
            'action': action,
            'args': args
        })
        return id

    def _get_responses(self, count):
        # The ActionRunnerPlugin will run the action in a thread, and call send_message when
        # it completes
        TIMEOUT = 2
        i = 0
        while True:
            if DevicePlugin.send_message.call_count >= count:
                break
            else:
                time.sleep(1)
                i += 1

            if i > TIMEOUT:
                raise AssertionError("Timed out after %ss waiting for %s responses (got %s)" % (TIMEOUT, count, DevicePlugin.send_message.call_count))

        self.assertEqual(DevicePlugin.send_message.call_count, count)
        return [args[0][0] for args in DevicePlugin.send_message.call_args_list]

    def test_run_action_runner(self):
        """
        Test that we can run an action in a thread using ActionRunnerPlugin (as
        the manager would via the HTTPS agent comms)
        """

        id = self._run_action('action_one', {'arg1': 'arg1_test'})
        response = self._get_responses(1)[0]
        self.assertDictEqual(response, {
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
