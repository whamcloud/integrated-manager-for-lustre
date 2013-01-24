
from chroma_core.models.registration_token import RegistrationToken
from chroma_core.models.host import ManagedHost
from chroma_core.models.server_profile import ServerProfile
from tests.unit.chroma_core.helper import MockAgentRpc

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.services.job_scheduler.job_test_case import JobTestCase


class TestRegistrationTokenResource(ChromaApiTestCase, JobTestCase):
    RESOURCE_PATH = "/api/host/"

    def setUp(self):
        super(TestRegistrationTokenResource, self).setUp()

        MockAgentRpc.mock_servers = {'foo': {
            'fqdn': 'myvm.mycompany.com',
            'nodename': 'test01.myvm.mycompany.com',
            'nids': ["192.168.0.19@tcp"]
        }}
        from tests.unit.chroma_core.helper import load_default_profile
        load_default_profile()

    def test_creation(self):
        response = self.api_client.post(self.RESOURCE_PATH, data={'address': 'foo', 'profile': 'default'})
        self.assertHttpAccepted(response)
        self.assertTrue(ManagedHost.objects.count())

    def test_creation_different_profile(self):
        test_sp = ServerProfile(name='test', ui_name='test UI',
            ui_description = 'a test description', managed = False, bundles = ['agent'])
        test_sp.save()
        response = self.api_client.post(self.RESOURCE_PATH, data={'address': 'foo', 'profile': 'test'})
        self.assertHttpAccepted(response)
        self.assertTrue(ManagedHost.objects.count())

        current_profile = RegistrationToken.objects.get().profile
        self.assertEquals(test_sp.name, current_profile.name)
        self.assertEquals(test_sp.ui_name, current_profile.ui_name)
        self.assertEquals(test_sp.managed, current_profile.managed)
        self.assertEquals(test_sp.bundles, current_profile.bundles)
