import json

import mock

from chroma_core.models import Job
from chroma_core.models import StepResult
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tests.unit.chroma_core.helpers.mock_agent_rpc import MockAgentRpc
from tests.unit.chroma_core.helpers.mock_agent_ssh import MockAgentSsh
from tests.unit.services.job_scheduler.job_test_case import JobTestCase


class TestHostAddValidations(JobTestCase):
    mock_servers = {
        "test-server": {
            "tests": {
                "auth": True,
                "resolve": True,
                "reverse_resolve": True,
                "ping": True,
                "reverse_ping": True,
                "hostname_valid": True,
                "fqdn_resolves": True,
                "fqdn_matches": True,
                "yum_can_update": True,
                "openssl": True,
            },
            "fqdn": "test-server.company.domain",
            "nodename": "test-server.company.domain",
            "address": "192.168.1.42",
        }
    }

    manager_http_url = "https://mock-manager.company.domain/"
    manager_address = "192.168.1.1"

    def setUp(self):
        super(TestHostAddValidations, self).setUp()
        self.maxDiff = None

        import settings

        settings.SERVER_HTTP_URL = self.manager_http_url

        def _gethostbyname(hostname):
            # Assume this is a lookup on manager of user-supplied hostname
            if hostname in self.mock_servers and self.mock_servers[hostname]["tests"]["resolve"]:
                return self.mock_servers[hostname]["address"]

            # Lookup from server of manager address
            if hostname in self.manager_http_url and self.mock_servers["test-server"]["tests"]["reverse_resolve"]:
                return self.manager_address

            if (
                hostname in self.mock_servers["test-server"].values()
                and self.mock_servers["test-server"]["tests"]["fqdn_resolves"]
            ):
                if self.mock_servers["test-server"]["tests"]["fqdn_matches"]:
                    return self.mock_servers["test-server"]["address"]
                else:
                    # Simulate a resolution mismatch
                    return "1.2.3.4"

            import socket

            raise socket.gaierror()

        patcher = mock.patch("socket.gethostbyname", _gethostbyname)
        patcher.start()

        def _subprocess_call(cmd):
            if "ping" in cmd:
                ping_address = cmd[-1]
                for server in self.mock_servers.values():
                    if ping_address == server["address"]:
                        return 0 if server["tests"]["ping"] else 1
                raise ValueError("Unable to find %s in test data" % ping_address)
            raise ValueError("Unable to mock cmd: %s" % " ".join(cmd))

        patcher = mock.patch("subprocess.call", _subprocess_call)
        patcher.start()

        # Reset to clean on each test
        for test in self.mock_servers["test-server"]["tests"]:
            self.mock_servers["test-server"]["tests"][test] = True
        MockAgentRpc.mock_servers = self.mock_servers
        MockAgentSsh.ssh_should_fail = False

        self.expected_result = {
            u"valid": True,
            u"address": u"test-server",
            u"profiles": {},
            "status": [
                {u"name": u"resolve", u"value": True},
                {u"name": u"ping", u"value": True},
                {u"name": u"auth", u"value": True},
                {u"name": u"hostname_valid", u"value": True},
                {u"name": u"fqdn_resolves", u"value": True},
                {u"name": u"fqdn_matches", u"value": True},
                {u"name": u"reverse_resolve", u"value": True},
                {u"name": u"reverse_ping", u"value": True},
                {u"name": u"yum_can_update", u"value": True},
                {u"name": u"openssl", u"value": True},
            ],
        }

        self.addCleanup(mock.patch.stopall)

    def _result_keys(self, excludes=[]):
        return [x["name"] for x in self.expected_result.get("status") if x["name"] not in excludes]

    def _inject_failures(self, failed_tests, extra_failures=[]):
        failed_results = failed_tests + extra_failures
        for test in failed_tests:
            self.mock_servers["test-server"]["tests"][test] = False
            if test == "auth":
                MockAgentSsh.ssh_should_fail = True

        for result in failed_results:
            x = next(x for x in self.expected_result["status"] if x["name"] == result)
            x["value"] = False

        self.expected_result["valid"] = False

    def test_host_no_problems(self):
        self.expected_result["profiles"]["test_profile"] = []
        self._test_host_contact()

    def test_unresolvable_server_name(self):
        self._inject_failures(["resolve"], self._result_keys())
        self._test_host_contact()

    def test_unpingable_server_name(self):
        # Expect everything after resolve to fail
        self._inject_failures(["ping"], self._result_keys(["resolve"]))
        self._test_host_contact()

    def test_auth_failure(self):
        # Expect everything after ping to fail
        self._inject_failures(["auth"], self._result_keys(["resolve", "ping"]))
        self._test_host_contact()

    def test_reverse_resolve_failure(self):
        # Expect reverse_resolve and reverse_ping to fail
        self._inject_failures(["reverse_resolve"], ["reverse_ping"])
        self._test_host_contact()

    def test_reverse_ping_failure(self):
        # Expect reverse_ping to fail
        self._inject_failures(["reverse_ping"])
        self._test_host_contact()

    def test_bad_hostname(self):
        # Expect hostname_valid, fqdn_resolves, and fqdn_matches to fail
        self._inject_failures(["hostname_valid"], ["fqdn_resolves", "fqdn_matches"])
        self._test_host_contact()

    def test_bad_fqdn(self):
        # Expect fqdn_resolves and fqdn_matches to fail
        self._inject_failures(["fqdn_resolves"], ["fqdn_matches"])
        self._test_host_contact()

    def test_fqdn_mismatch(self):
        # Expect fqdn_matches to fail
        self._inject_failures(["fqdn_matches"])
        self._test_host_contact()

    def test_yum_update_failure(self):
        # Expect yum_can_update to fail
        self._inject_failures(["yum_can_update"])
        self._test_host_contact()

    def _test_host_contact(self):

        command = JobSchedulerClient.test_host_contact("test-server")
        self.drain_progress()

        job = Job.objects.filter(command__pk=command.id)[0]
        step_result = StepResult.objects.filter(job__pk=job.id)[0]

        self.assertEqual(self.expected_result, json.loads(step_result.result))
