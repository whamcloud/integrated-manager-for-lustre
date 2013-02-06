from chroma_core.models.registration_token import RegistrationToken
import settings
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCaseHeavy
from tests.unit.chroma_core.helper import MockAgentRpc, generate_csr


# FIXME: this stuff shouldn't really be in chroma_api as it's testing
# other HTTP-accessed things


class TestRegistration(ChromaApiTestCaseHeavy):
    """API unit tests for functionality used only by the agent"""

    def test_version(self):
        versions = settings.VERSION, MockAgentRpc.version
        settings.VERSION, MockAgentRpc.version = '2.0', '1.0'

        self.mock_servers = {'mynewhost': {
            'fqdn': 'mynewhost.mycompany.com',
            'nodename': 'test01.mynewhost.mycompany.com',
            'nids': ["192.168.0.1@tcp"]
        }}

        try:
            token = RegistrationToken.objects.create()

            host_info = self.mock_servers['mynewhost']
            response = self.api_client.post("/agent/register/%s/" % token.secret, data = {
                'fqdn': host_info['fqdn'],
                'nodename': host_info['nodename'],
                'version': MockAgentRpc.version,
                'capabilities': ['manage_targets'],
                'address': 'mynewhost',
                'csr': generate_csr(host_info['fqdn'])
            })
            self.assertHttpBadRequest(response)

            token = RegistrationToken.objects.create()

            settings.VERSION = '1.1'
            response = self.api_client.post("/agent/register/%s/" % token.secret, data = {
                'fqdn': host_info['fqdn'],
                'nodename': host_info['nodename'],
                'version': MockAgentRpc.version,
                'capabilities': ['manage_targets'],
                'address': 'mynewhost',
                'csr': generate_csr(host_info['fqdn'])
            })
            self.assertHttpCreated(response)

        finally:
            settings.VERSION, MockAgentRpc.version = versions

# TOOD: reinstate selinux check, probably within the agent itself (it should fail
# its own registration step without even talking to the manager)
#    def test_selinux_detection(self):
#        """Test that a host with SELinux enabled fails setup."""
#        MockAgentRpc.selinux_enabled = True
#        try:
#            import time
#            host = self._create_host('myaddress')
#            self.assertTrue(Command.objects.all().order_by("-id")[0].errored)
#            self.assertState(host, 'unconfigured')
#        finally:
#            MockAgentRpc.selinux_enabled = False
