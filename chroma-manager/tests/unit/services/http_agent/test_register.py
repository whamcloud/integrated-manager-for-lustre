import json
from chroma_core.models.registration_token import RegistrationToken
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from django.test import Client, TestCase
import mock
import settings
from tests.unit.chroma_core.helper import MockAgentRpc, generate_csr, synthetic_host


class TestRegistration(TestCase):
    """API unit tests for functionality used only by the agent"""

    def setUp(self):
        super(TestRegistration, self).setUp()
        self.old_create_host = JobSchedulerClient.create_host
        JobSchedulerClient.create_host = mock.Mock(return_value=(synthetic_host('mynewhost'), mock.Mock(id='bar')))

    def tearDown(self):
        JobSchedulerClient.create_host = self.old_create_host

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

            # Try with a mis-matched version
            host_info = self.mock_servers['mynewhost']
            response = Client().post("/agent/register/%s/" % token.secret, data=json.dumps({
                'fqdn': host_info['fqdn'],
                'nodename': host_info['nodename'],
                'version': MockAgentRpc.version,
                'capabilities': ['manage_targets'],
                'address': 'mynewhost',
                'csr': generate_csr(host_info['fqdn'])
            }), content_type="application/json")
            self.assertEqual(response.status_code, 400)

            # Try with a matching version
            token = RegistrationToken.objects.create()
            settings.VERSION = '1.1'
            response = Client().post("/agent/register/%s/" % token.secret, data=json.dumps({
                'fqdn': host_info['fqdn'],
                'nodename': host_info['nodename'],
                'version': MockAgentRpc.version,
                'capabilities': ['manage_targets'],
                'address': 'mynewhost',
                'csr': generate_csr(host_info['fqdn'])
            }), content_type="application/json")
            self.assertEqual(response.status_code, 201)

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
