import json
import contextlib
import mock

from chroma_api.urls import api
from chroma_core.models import Bundle, Command
from chroma_core.models.host import ManagedHost, Nid
from chroma_core.models.server_profile import ServerProfile, ServerProfileValidation
from chroma_core.services.job_scheduler import job_scheduler_client

from tests.unit.chroma_core.helper import MockAgentRpc, create_host_ssh_patch, synthetic_host, make_command
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestHostResource(ChromaApiTestCase):
    RESOURCE_PATH = "/api/host/"

    def setUp(self):
        super(TestHostResource, self).setUp()

        MockAgentRpc.mock_servers = {'foo': {
            'fqdn': 'foo.mycompany.com',
            'nodename': 'test01.foo.mycompany.com',
            'nids': [Nid.Nid("192.168.0.19", "tcp", 0)]
        },
                                     'bar': {
            'fqdn': 'bar.mycompany.com',
            'nodename': 'test01.bar.mycompany.com',
            'nids': [Nid.Nid("192.168.0.91", "tcp", 0)]
        }}

    @create_host_ssh_patch
    def test_creation_single(self):
        host_count = 0

        for key in MockAgentRpc.mock_servers:
            response = self.api_client.post(self.RESOURCE_PATH, data={'address': key,
                                                                      'server_profile': '/api/server_profile/test_profile/'})
            host_count += 1
            self.assertHttpAccepted(response)
            self.assertEqual(ManagedHost.objects.count(), host_count)

    @create_host_ssh_patch
    def test_creation_multiple(self):
        response = self.api_client.post(self.RESOURCE_PATH, data={'objects': [{'address': host_name} for host_name in MockAgentRpc.mock_servers],
                                                                  'server_profile': '/api/server_profile/test_profile/'})
        self.assertHttpAccepted(response)
        content = json.loads(response.content)
        self.assertEqual(content['errors'], [None] * len(MockAgentRpc.mock_servers))
        self.assertEqual(map(sorted, content['objects']), [['command', 'host']] * len(MockAgentRpc.mock_servers))

    @create_host_ssh_patch
    def test_creation_different_profile(self):
        test_sp = ServerProfile(name='test', ui_name='test UI',
                                ui_description='a test description', managed=False)
        test_sp.save()
        test_sp.bundles.add(Bundle.objects.get(bundle_name='agent'))

        response = self.api_client.post(self.RESOURCE_PATH, data={'address': 'foo', 'server_profile': '/api/server_profile/test/'})
        self.assertHttpAccepted(response)
        self.assertTrue(ManagedHost.objects.count())

        current_profile = ManagedHost.objects.get().server_profile
        self.assertEquals(test_sp.name, current_profile.name)
        self.assertEquals(test_sp.ui_name, current_profile.ui_name)
        self.assertEquals(test_sp.managed, current_profile.managed)
        self.assertEquals(list(test_sp.bundles.all()), list(current_profile.bundles.all()))

    @create_host_ssh_patch
    def test_profile(self):
        validations = [{'test': 'variable1 == 1', 'description': 'variable1 should equal 1'},
                       {'test': 'variable2 == 2', 'description': 'variable2 should equal 2'}]

        with mock.patch('chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.test_host_contact', mock.Mock()) as thc:
            def test_host_contact(*args, **kwargs):
                return Command.objects.create(message="No-op", complete=True)
            thc.side_effect = test_host_contact

            # Test a single post.
            for key in MockAgentRpc.mock_servers:
                response = self.api_client.post('/api/test_host/', data={'address': [key]})
                self.assertHttpAccepted(response)
                content = json.loads(response.content)
                self.assertEqual(len(content['objects']), 1)

            # The code below should work but needs implementation of bulk post which comes later
            # however the code was written before I realise that wasn't done either. HYD-3584
            # HYD-3584 is a must do for 2.2
            if False:
                ManagedHost.objects.all().delete()

                # Test a batch post.
                response = self.api_client.post('/api/test_host/', data={'objects': {'address': ['foo'],
                                                                                     'address': ['bar']}})
                self.assertHttpAccepted(response)
                content = json.loads(response.content)
                self.assertEqual(content['errors'], [None])
                self.assertEqual(len(content['objects']), 1)

        for profile in ServerProfile.objects.all():
            for validation in validations:
                profile.serverprofilevalidation_set.add(ServerProfileValidation(**validation))
        profile = ServerProfile(name='default', ui_name='Default', ui_description='Default', managed=False, user_selectable=False)
        profile.save()
        profile.bundles.add(Bundle.objects.get(bundle_name='agent'))

        response = self.api_client.post(self.RESOURCE_PATH, data={'objects': [{'address': host_name} for host_name in MockAgentRpc.mock_servers]})
        self.assertHttpAccepted(response)
        content = json.loads(response.content)
        self.assertEqual(content['errors'], [None] * len(MockAgentRpc.mock_servers))
        self.assertEqual(map(sorted, content['objects']), [['command', 'host']] * len(MockAgentRpc.mock_servers))

        hosts = ManagedHost.objects.all()
        self.assertEqual(hosts[0].server_profile.name, 'default')

        # Check we no properties, both should fail.
        for validation in validations:
            validation['pass'] = False
            validation['error'] = 'Result unavailable while host agent starts'

        response = self.api_client.get('/api/host_profile/{0}/'.format(hosts[0].id))
        self.assertHttpOK(response)
        content = json.loads(response.content)
        content['test_profile'].sort()
        validations.sort()
        self.assertEqual(content['test_profile'], validations)

        # Now set the first property = variable1 = 1
        for host in hosts:
            host.properties = json.dumps({'variable1': 1})
            host.save()

        # And change the validation.
        self.assertEqual(validations[0]['test'], 'variable1 == 1')
        validations[0]['pass'] = True
        validations[0]['error'] = ''
        validations[1]['error'] = 'zero length field name in format'

        response = self.api_client.get('/api/host_profile/{0}/'.format(hosts[0].id))
        self.assertHttpOK(response)
        content = json.loads(response.content)
        content['test_profile'].sort()
        validations.sort()
        self.assertEqual(content['test_profile'], validations)

        for data in ({}, {'id__in': [hosts[0].id, 0]}):
            response = self.api_client.get('/api/host_profile/', data=data)
            self.assertHttpOK(response)
            objects = json.loads(response.content)['objects']

            host_index = 0

            for object in objects:
                object['profiles']['test_profile'].sort()
                validations.sort()
                self.assertEqual(object, {'profiles': {'test_profile': validations}, 'host': hosts[host_index].id, 'address': hosts[host_index].address})
                host_index += 1

        def _mock_jsc_set_host_profile(host_id, server_profile_id):
            ManagedHost.objects.filter(id = host_id).update(server_profile = server_profile_id)

            return make_command(dismissed=False, complete=False, created_at=None, failed=True, message='test')

        def _mock_command_set_state(objects, message = None, **kwargs):
            for object, state in objects:
                object.__class__.objects.filter(id = object.id).update(state = state)

            return make_command(dismissed=False, complete=False, created_at=None, failed=True, message='test')

        # Place the host into the unconfigured state, this is typical of where it will be at this point.
        ManagedHost.objects.filter(id = hosts[0].id).update(state = 'unconfigured')

        with contextlib.nested(mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.set_host_profile",
                                          new = mock.Mock(side_effect = _mock_jsc_set_host_profile)),
                               mock.patch("chroma_core.models.Command.set_state",
                                          new = mock.Mock(side_effect = _mock_command_set_state))) as (shp, ccs):

            response = self.api_client.put('/api/host_profile/{0}/'.format(hosts[0].id), data={'profile': 'test_profile'})
            self.assertHttpAccepted(response)
            content = json.loads(response.content)
            self.assertEqual(len(content['objects']), 2)
            self.assertEqual(ManagedHost.objects.get(id=hosts[0].id).server_profile.name, 'test_profile')
            shp.assert_called_once_with(hosts[0].id, u"test_profile")
            ccs.assert_called_once_with([(hosts[0], u'configured')])

            shp.reset_mock()
            ccs.reset_mock()

            # Reset the profile and state
            ManagedHost.objects.filter(id = hosts[0].id).update(state = 'unconfigured', server_profile = 'default')

            response = self.api_client.post('/api/host_profile/', data={'objects': [{'host': host.id, 'profile': 'test_profile'} for host in hosts]})
            self.assertHttpAccepted(response)
            content = json.loads(response.content)

            # 3 commands because host[0] is already in the correct state so just needs the profile changed, host[1] needs profile and state changed.
            self.assertEqual(len(content['objects']), 3)
            self.assertEqual(ManagedHost.objects.get(id=hosts[0].id).server_profile.name, 'test_profile')
            self.assertEqual(shp.call_count, 2)
            self.assertEqual(ccs.call_count, 1)

            shp.reset_mock()
            ccs.reset_mock()

            # If we do it once more we should have no effect because the profile is already set.
            response = self.api_client.post('/api/host_profile/', data={'objects': [{'host': host.id, 'profile': 'test_profile'} for host in hosts]})
            self.assertHttpAccepted(response)
            content = json.loads(response.content)

            self.assertEqual(len(content['objects']), 0)
            self.assertEqual(ManagedHost.objects.get(id=hosts[0].id).server_profile.name, 'test_profile')
            self.assertEqual(shp.called, False)
            self.assertEqual(ccs.called, False)


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
    """Test HostResource and TestHostResource passing through SSH auth
    arguments in the expected form to JobSchedulerClient.
    """
    def __init__(self, method, username='admin', **kwargs):
        ChromaApiTestCase.__init__(self, method, username=username, **kwargs)

    def setUp(self):
        super(TestCreateHostAPI, self).setUp()

        # Body for a POST to either host or test_host
        self.input_data = {"address": 'myaddress',
                           "auth_type": 'existing_keys_choice',
                           "server_profile": api.get_resource_uri(ServerProfile.objects.get()),
                           "root_password": 'secret_pw',
                           "private_key": sample_private_key,
                           "private_key_passphrase": 'secret_key_pw'}

    def tearDown(self):
        super(TestCreateHostAPI, self).tearDown()

    def _create_host(self):
        ManagedHost.objects.create(state = 'undeployed',
                                   address = 'myaddress',
                                   nodename = 'myaddress',
                                   fqdn = 'myaddress',
                                   immutable_state = False,
                                   install_method = ManagedHost.INSTALL_MANUAL)

    def test_host_contact_ssh_auth_accept_not_present_no_check(self):
        self._test_host_contact_ssh_auth(True)

    def test_host_contact_ssh_auth_accept_present_no_check(self):
        self._create_host()
        self._test_host_contact_ssh_auth(True)

    def test_host_contact_ssh_auth_accept_not_present_check(self):
        self.input_data["host_must_exist"] = False
        self._test_host_contact_ssh_auth(True)

    def test_host_contact_ssh_auth_accept_present_check(self):
        self._create_host()
        self.input_data["host_must_exist"] = True
        self._test_host_contact_ssh_auth(True)

    def test_host_contact_ssh_auth_reject_present_check(self):
        self._create_host()
        self.input_data["host_must_exist"] = False
        self._test_host_contact_ssh_auth(False)

    def test_host_contact_ssh_auth_reject_not_present_check(self):
        self.input_data["host_must_exist"] = True
        self._test_host_contact_ssh_auth(False)

    def _test_host_contact_ssh_auth(self, accept):
        """Test POST to /api/test_host/ results in jobschedulerclient call."""
        with mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.test_host_contact", mock.Mock()) as thc:
            def test_host_contact(*args, **kwargs):
                return Command.objects.create(message="No-op", complete=True)
            thc.side_effect = test_host_contact

            api_resp = self.api_client.post("/api/test_host/", data=self.input_data)

            if accept:
                self.assertHttpAccepted(api_resp)

                thc.assert_called_once_with(**{"address": 'myaddress',
                                               "root_pw": 'secret_pw',
                                               "pkey": sample_private_key,
                                               "pkey_pw": 'secret_key_pw'})
            else:
                self.assertHttpBadRequest(api_resp)

                self.assertEqual(thc.call_count, 0, "test_host_contact called %s != 0 for failing case" % thc.call_count)

        # Create object so that on the second time round we check the false case.

    def test_create_host_api_ssh_auth(self):
        """Test POST to /api/host/ results in jobschedulerclient call."""

        with mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.create_host_ssh", mock.Mock()) as chs:
            # Got to return something here for API to dehydrate its response
            def create_host_ssh(*args, **kwargs):
                return synthetic_host(kwargs['address']), Command.objects.create()
            chs.side_effect = create_host_ssh

            response = self.api_client.post("/api/host/", data=self.input_data)
            self.assertHttpAccepted(response)
            job_scheduler_client.JobSchedulerClient.create_host_ssh.assert_called_once_with(
                **{"address": 'myaddress',
                   "server_profile": ServerProfile.objects.get().name,
                   "root_pw": 'secret_pw',
                   "pkey": sample_private_key,
                   "pkey_pw": 'secret_key_pw'}
            )
