from chroma_core.models import Bundle
from chroma_core.models.host import ManagedHost
from chroma_core.models.server_profile import ServerProfile
from tests.unit.chroma_core.helper import MockAgentRpc, create_host_ssh_patch

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestHostResource(ChromaApiTestCase):
    RESOURCE_PATH = "/api/host/"

    def setUp(self):
        super(TestHostResource, self).setUp()

        MockAgentRpc.mock_servers = {'foo': {
            'fqdn': 'myvm.mycompany.com',
            'nodename': 'test01.myvm.mycompany.com',
            'nids': ["192.168.0.19@tcp"]
        }}

    @create_host_ssh_patch
    def test_creation(self):
        response = self.api_client.post(self.RESOURCE_PATH, data={'address': 'foo', 'profile': 'default'})
        self.assertHttpAccepted(response)
        self.assertTrue(ManagedHost.objects.count())

    @create_host_ssh_patch
    def test_creation_different_profile(self):
        test_sp = ServerProfile(name='test', ui_name='test UI',
                                ui_description='a test description', managed=False)
        test_sp.save()
        test_sp.bundles.add(Bundle.objects.get(bundle_name='agent'))

        response = self.api_client.post(self.RESOURCE_PATH, data={'address': 'foo', 'profile': 'test'})
        self.assertHttpAccepted(response)
        self.assertTrue(ManagedHost.objects.count())

        current_profile = ManagedHost.objects.get().server_profile
        self.assertEquals(test_sp.name, current_profile.name)
        self.assertEquals(test_sp.ui_name, current_profile.ui_name)
        self.assertEquals(test_sp.managed, current_profile.managed)
        self.assertEquals(list(test_sp.bundles.all()), list(current_profile.bundles.all()))
