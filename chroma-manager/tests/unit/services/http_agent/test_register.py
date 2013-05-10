import json
from chroma_core.models import ManagedHost, ServerProfile
from chroma_core.models.registration_token import RegistrationToken
from chroma_core.services.http_agent.crypto import Crypto
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_agent_comms.views import MessageView
from django.test import Client, TestCase
import mock
import settings
from tests.unit.chroma_core.helper import MockAgentRpc, generate_csr, synthetic_host, load_default_profile


class TestRegistration(TestCase):
    """API unit tests for functionality used only by the agent"""
    mock_servers = {'mynewhost': {
        'fqdn': 'mynewhost.mycompany.com',
        'nodename': 'test01.mynewhost.mycompany.com',
        'nids': ["192.168.0.1@tcp"],
    }}

    def setUp(self):
        super(TestRegistration, self).setUp()

        load_default_profile()

        self.old_create_host = JobSchedulerClient.create_host
        JobSchedulerClient.create_host = mock.Mock(side_effect=lambda *args, **kwargs: (synthetic_host('mynewhost', **self.mock_servers['mynewhost']), mock.Mock(id='bar')))
        MessageView.valid_certs = {}

    def tearDown(self):
        JobSchedulerClient.create_host = self.old_create_host

    def test_version(self):
        versions = settings.VERSION, MockAgentRpc.version
        settings.VERSION, MockAgentRpc.version = '2.0', '1.0'

        try:
            token = RegistrationToken.objects.create(profile=ServerProfile.objects.get())

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
            token = RegistrationToken.objects.create(profile=ServerProfile.objects.get())
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
            content = json.loads(response.content)

            # reregistration should fail with unknown serial
            data = {'address': 'mynewhost', 'fqdn': 'mynewhost.newcompany.com'}
            headers = {'HTTP_X_SSL_CLIENT_NAME': host_info['fqdn'], 'HTTP_X_SSL_CLIENT_SERIAL': ''}
            response = Client().post('/agent/reregister/', data=json.dumps(data), content_type='application/json', **headers)
            self.assertEqual(response.status_code, 403)

            # reregistration should update host's domain name
            headers['HTTP_X_SSL_CLIENT_SERIAL'] = Crypto().get_serial(content['certificate'])
            response = Client().post('/agent/reregister/', data=json.dumps(data), content_type='application/json', **headers)
            self.assertEqual(response.status_code, 200)
            host = ManagedHost.objects.get(id=content['host_id'])
            self.assertEqual(host.fqdn, data['fqdn'])

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
