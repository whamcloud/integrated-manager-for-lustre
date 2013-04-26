from chroma_core.models import Bundle
from chroma_core.models.host import ManagedHost
from chroma_core.models.server_profile import ServerProfile
from chroma_core.services.job_scheduler import job_scheduler_client

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


sample_private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAwkuskn4QIxHVKcDqN7wIhedt2HxCJg2PZ2N8goUaJwVd6uU3
p5ZwJrdIc7SwIRqTnRGcq/P8mClXoNeLyGfei0b9UEmtioVDB1Qb2iOuTx0FEz+x
L20vchkV2Zkg4u6cKBt6ATPuesQvq+ok2wXYsbF18xYiRBQbPVHT7Dow5jswoaL5
eVszYsa87E6PTIDfNNmQQWf3bYbDMgx9i1kj+hxENeMPfX7JwPt00ZO+raxBmHH0
Q+7Xger8tvTvuJ8f18umoTTfSUTxOQ3nW7en2dhHA9Pow0bRkn36lWx/mrUpsaVS
1bjkaCrrXMccsuvn7y2GKh3P1QpptZSBX8XDWQIDAQABAoIBADH8wChsUICFTP9S
B7BRKywwL32b8nTR1kw2N0lpLyJM6i3NzTTLqoz7aKOEIDBUIxgs+M7wldMcB9R0
705+QZLt4jepQSWcuqlbDRfgnXXOjzAIO4WfDxzXaomAVZvwOlXYeDNmok+hERxM
S+VNzKuy19P7Caa0+Z5MSP0ebqfu1V2dnQcaPj/0umo4g651VQskZU8Cuz0R8Xb5
DZCcrCmECU+/R3yuotSVSKsr1RizsIeR1mxlIQ2dXLKRzKVmanOnjpTUdRkI8059
kQEDB5UCgYEA83xdXPL4aO25GzJCBeGSOBZWkcqI5zZeH3zttBi5OTHRYHNR7k9z
8GjqNPgOk7Fw9N2/XhHFvRwxIXFe0pcxFHXqEPLnOfuhpR3TfDAOI18w6OceV/ay
OHY9QypYzJQUnxJMxxfvddmJfc+zfurOaV7SPVd5iFXJQUlN97gz4gsCgYEAzEgY
Y10A5SaA9LAPfuwQ2xrDs/5taHRyV3AbhQYxS15t2Rqw3hr6bmf+61HqKx3LMwhr
ZjEUFaRfCqS5UxddBEjiI73hYytWOG413upXaVRAx2jIONB+7Jkhht8VF5MWhloi
55B815jIHAEgr4MrHaKABg60dyYhORJstyJLEqsCgYEAqBALkYDUHfkYb8E8+To9
5yDkGDWoUY+hYDKnEEyQbP4J+30d7FRDPonsPyuJRECSKzJ0SMYTqviuoNrUDJ/3
bJwHODOxjsA1TvdLZsj0uU2XQOtmcmkBkx9qIdY0/OCpazMCc9n9m2bQFFstFkmU
t/6PN3ANnyE3jSy/+GDYzwkCgYEAox4ycy0xaMkNEdWAGh4P+5Tsjk5sOIs7Pjyj
jN38AK2/Uyuv7TpnnD9oW6lGLfWVawOfFrO70Og2h/4uiX3PZXt5L4cQcSqKp3bB
h2ViNRX0wAYYUt2RbAV+sv5xDikCRHe3BWbneRRjPZFc8yjvBbPbPHsDeVy2DKd8
reMxRQ8CgYBbxxoejSHA9bdwMysa01auk/ypwBdPX+kI4sCwygg83iDrdtp5zT3J
xQHxeLJXMYPFKnJvofvHGBhHGGZpJHDFl6/ZdEnyCLukDbcrFq5K1nQ0dD4AhKD9
rBxijqhV7HZNBMbgrttwG0KVhyqb3XdveevUpL3VMgpRxZ3Sgf2wMQ==
-----END RSA PRIVATE KEY-----"""


class TestCreateHostAPI(ChromaApiTestCase):
    """Test ssh auth - API Resource /api/host and /api/test_host to job client

    Test that if the ssh auth params are given from the UI to the API,
    the params will be passed to the JobSchedulerClient.
    """

    class MockJobSchedulerClient(object):
        """Simulate the signature of the JobSchedulerClient methods

        This sim allows code above like the API to test the interface
        JobSchedulerClient interface.
        """

        #  Test that the client will receive the correct paramaters

        tester = None

        @classmethod
        def _check_params(cls, address, profile = None, root_pw=None,
                          pkey=None, pkey_pw=None):
            cls.tester.assertEquals(address, cls.tester.expected_data['address'])
            if profile is not None:
                cls.tester.assertEquals(profile, cls.tester.expected_data['profile'])
            cls.tester.assertEquals(root_pw, cls.tester.expected_data['root_password'])
            cls.tester.assertEquals(pkey, cls.tester.expected_data['private_key'])
            cls.tester.assertEquals(pkey_pw, cls.tester.expected_data['private_key_passphrase'])

        @classmethod
        def create_host_ssh(cls, address, profile, root_pw=None,
                            pkey=None, pkey_pw=None):
            cls.got_called = True
            cls._check_params(address, profile, root_pw, pkey, pkey_pw)
            raise Exception("Passes")

        @classmethod
        def test_host_contact(cls, address, root_pw=None,
                              pkey=None, pkey_pw=None):
            cls.got_called = True
            cls._check_params(address, root_pw=root_pw, pkey=pkey, pkey_pw=pkey_pw)

    def setUp(self):
        super(TestCreateHostAPI, self).setUp()

        self.old_jobSchedulerClient = job_scheduler_client.JobSchedulerClient
        job_scheduler_client.JobSchedulerClient = TestCreateHostAPI.MockJobSchedulerClient
        job_scheduler_client.JobSchedulerClient.got_called = False
        job_scheduler_client.JobSchedulerClient.tester = self

        self.expected_data = {"address": 'storage1',
                              "profile": ServerProfile.objects.get().name,
                              "root_password": 'secret_pw',
                              "private_key": sample_private_key,
                              "private_key_passphrase": 'secret_key_pw'}

    def tearDown(self):
        super(TestCreateHostAPI, self).tearDown()

        job_scheduler_client.JobSchedulerClient = self.old_jobSchedulerClient

    def test_host_contact_ssh_auth(self):
        """Test POST to /api/test_host/ results in jobschedulerclient call."""

        api_resp = self.api_client.post("/api/test_host/", data = self.expected_data)
        self.assertHttpAccepted(api_resp)
        self.assertTrue(job_scheduler_client.JobSchedulerClient.got_called)

    def test_create_host_api_ssh_auth(self):
        """Test POST to /api/host/ results in jobschedulerclient call."""

        self.api_client.post("/api/host/", data = self.expected_data)
        self.assertTrue(job_scheduler_client.JobSchedulerClient.got_called)
