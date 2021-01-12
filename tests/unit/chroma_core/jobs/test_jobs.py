import mock

from tests.unit.chroma_core import helpers

from chroma_core.lib.job import Step
from chroma_core.services.log import log_register
from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase
from emf_common.lib.agent_rpc import agent_result, agent_result_ok, agent_error

log = log_register("emf_test_case")


class TestJobs(EMFUnitTestCase):
    def __init__(self, methodName="runTest"):
        super(TestJobs, self).__init__(methodName=methodName)

        self.hosts = []
        self._missing_invoke_err_msg = "Invoke attempted was unknown to InvokeCaptureTestCase, did you intend this?"
        self.mock_job = mock.MagicMock()
        self._invokes = []

    def setUp(self):
        super(TestJobs, self).setUp()

        helpers.load_default_profile()

        for host_id in range(0, 10):
            host = helpers.synthetic_host(address="myserver%s" % host_id)
            self.hosts.append(host)

        self.reset_invoke_capture()

        assert "fake" not in str(Step.invoke_agent)

        mock.patch("chroma_core.lib.job.Step.invoke_agent", self._fake_invoke_agent).start()

        self.addCleanup(mock.patch.stopall)

    @property
    def host(self):
        # Handy if you're only using one
        return self.hosts[0]

    @property
    def host_ids(self):
        return [host.id for host in self.hosts]

    def _fake_invoke_agent(self, host, invoke, args=None):
        args = args if args is not None else {}

        assert type(args) is dict, "args list must be dict :%s" % type(args)

        args = InvokeAgentInvoke(host, invoke, args, None, None)

        self._invokes_history.append(args)

        result = self._get_executable_invoke(args)
        result.executions_remaining -= 1

        if result.error:
            return agent_error(result.error)

        if result.result:
            return agent_result(result.result)

        return agent_result_ok

    def _get_executable_invoke(self, args):
        """
        return the invoke whose args match those given. note that exact order match is needed

        FIXME: return more information about whether invoke was nearly correct compare each
        invoke in list, print the one that's closest rather than just 'no such...'

        :param args: Tuple of the arguments of the invoke
        :return: The invoke requested or raise a KeyError
        """
        for invoke in self._invokes:
            if invoke == args and invoke.executions_remaining > 0:
                return invoke
        raise KeyError

    def assertRanInvoke(self, invoke):
        """
        assert that the invoke made up of the args passed was executed.
        :param invoke: The invoke to check
        """
        self.assertTrue(invoke in self._invokes_history)

    def assertRanAllInvokesInOrder(self):
        """
        assert that all the invokes expected were run in the order expected.
        """
        self.assertEqual(len(self._invokes), len(self._invokes_history))

        for ran, expected in zip(self._invokes, self._invokes_history):
            self.assertEqual(ran, expected)

    def assertRanAllInvokes(self):
        """
        assert that all the invokes expected were run, the order is not important.
        Some invokes may be run more than once.
        """
        invokes_history = set(self._invokes_history)

        self.assertEqual(len(self._invokes), len(invokes_history))

        for invoke in self._invokes:
            self.assertRanInvoke(invoke)

    def add_invokes(self, *invokes):
        """
        Add a list of invoke that is expected to be run.
        :param *invokes: invokeCaptureinvoke args of invokes to be run
        :return: No return value
        """
        for invoke in invokes:
            self._invokes.append(invoke)

    def add_invoke(self, host_fqdn, invoke, args, result, error, executions_remaining=999999):
        """
        Add a single invoke that is expected to be run.
        :param args: Tuple of the arguments of the invoke
        :param rc: return of the invoke
        :param stdout: stdout for the invoke
        :param stderr: stderr for the invoke
        :return: No return value
        """
        self.add_invokes(InvokeAgentInvoke(host_fqdn, invoke, args, result, error, executions_remaining))

    @property
    def invokes_ran_count(self):
        return len(self._invokes_history)

    def reset_invoke_capture(self):
        """
        Reset the invoke capture to the initialized state.
        :return: None
        """
        self._invokes = []
        self.reset_invoke_capture_logs()

    def reset_invoke_capture_logs(self):
        """
        Reset the invoke capture logs to the initialized state.
        :return: None
        """
        self._invokes_history = []

    def run_step(self, job, step):
        step[0](job, step[1], None, None, None).run(step[1])


class InvokeAgentInvoke(object):
    def __init__(self, host_fqdn, command, args, result, error, executions_remaining=999999):
        self.host_fqdn = host_fqdn
        self.command = command
        self.args = args
        self.result = result
        self.error = error
        self.executions_remaining = executions_remaining

    def __eq__(self, other):
        return self.host_fqdn == other.host_fqdn and self.command == other.command and self.args == other.args
