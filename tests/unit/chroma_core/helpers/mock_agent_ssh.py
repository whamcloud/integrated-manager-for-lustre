from chroma_core.models import ManagedHost
from chroma_core.services.log import log_register
from tests.unit.chroma_core.helpers.mock_agent_rpc import MockAgentRpc

log = log_register("mock_agent_ssh")


class MockAgentSsh(object):
    ssh_should_fail = False

    def __init__(self, address, log=None, console_callback=None, timeout=None):
        self.address = address

    def construct_ssh_auth_args(self, root_pw, pkey, pkey_pw):
        return {}

    def invoke(self, cmd, args={}, auth_args=None):
        host = ManagedHost(address=self.address)
        return MockAgentRpc._call(host, cmd, args)

    def ssh(self, cmd, auth_args=None):
        if self.ssh_should_fail:
            from paramiko import SSHException

            raise SSHException("synthetic failure")

        result = self.invoke(cmd, auth_args)
        if isinstance(result, int):
            return (result, "", "")
        else:
            return (0, result, "")

    def ssh_params(self):
        return "root", self.address, 22
