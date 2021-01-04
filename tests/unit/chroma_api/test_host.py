import json

import mock

from chroma_api.urls import api
from chroma_core.models import Command
from chroma_core.models import ManagedHost
from chroma_core.models import Nid
from chroma_core.models import ServerProfile, ServerProfileValidation
from chroma_core.services.job_scheduler import job_scheduler_client
from tests.unit.chroma_core.helpers.mock_agent_rpc import MockAgentRpc
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host, create_host_ssh_patch
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestHostResource(ChromaApiTestCase):
    RESOURCE_PATH = "/api/host/"

    def setUp(self):
        super(TestHostResource, self).setUp()

        MockAgentRpc.mock_servers = {
            "foo": {
                "fqdn": "foo.mycompany.com",
                "nodename": "test01.foo.mycompany.com",
                "nids": [Nid.Nid("192.168.0.19", "tcp", 0)],
            },
            "bar": {
                "fqdn": "bar.mycompany.com",
                "nodename": "test01.bar.mycompany.com",
                "nids": [Nid.Nid("192.168.0.91", "tcp", 0)],
            },
        }

    @create_host_ssh_patch
    def test_creation_single(self):
        host_count = 0

        for key in MockAgentRpc.mock_servers:
            response = self.api_client.post(
                self.RESOURCE_PATH, data={"address": key, "server_profile": "/api/server_profile/test_profile/"}
            )
            host_count += 1
            self.assertHttpAccepted(response)
            self.assertEqual(ManagedHost.objects.count(), host_count)

    def test_update_single(self):
        self.test_creation_single()

        for host in ManagedHost.objects.all():
            response = self.api_client.put("%s%s/" % (self.RESOURCE_PATH, host.id), data={"state": host.state})
            self.assertHttpNoContent(response)  # No content because there is no state change.

    def test_update_single_fail(self):
        self.test_creation_single()

        for host in ManagedHost.objects.all():
            response = self.api_client.put("%s%s/" % (self.RESOURCE_PATH, host.id), data={})
            self.assertHttpBadRequest(response)  # No content because there is not state change.
            self.assertTrue("State data not present" in response.content)

    @create_host_ssh_patch
    def test_creation_bulk(self):
        response = self.api_client.post(
            self.RESOURCE_PATH,
            data={
                "objects": [
                    {"address": host_name, "server_profile": "/api/server_profile/test_profile/"}
                    for host_name in MockAgentRpc.mock_servers
                ]
            },
        )
        self.assertHttpAccepted(response)
        self.assertEqual(ManagedHost.objects.count(), len(MockAgentRpc.mock_servers))

        content = json.loads(response.content)

        self.assertEqual(len(content["objects"]), len(MockAgentRpc.mock_servers))

        for object in content["objects"]:
            self.assertEqual(object["error"], None)
            self.assertEqual(object["traceback"], None)
            self.assertEqual(object["command_and_host"].keys(), ["host", "command"])

    def test_update_bulk(self):
        self.test_creation_bulk()

        for host in ManagedHost.objects.all():
            host.state = "undeployed"
            host.save()

        with create_host_ssh_patch:
            response = self.api_client.put(
                self.RESOURCE_PATH,
                data={
                    "objects": [
                        {"address": host.address, "server_profile": "/api/server_profile/test_profile/"}
                        for host in ManagedHost.objects.all()
                    ]
                },
            )

        self.assertHttpAccepted(response)
        self.assertEqual(ManagedHost.objects.count(), len(MockAgentRpc.mock_servers))

        content = json.loads(response.content)

        self.assertEqual(len(content["objects"]), len(MockAgentRpc.mock_servers))

        for object in content["objects"]:
            self.assertEqual(object["error"], None)
            self.assertEqual(object["traceback"], None)
            self.assertEqual(object["command_and_host"].keys(), ["host", "command"])

    def create_host_ssh_fail_patch(self, address, server_profile, root_pw=None, pkey=None, pkey_pw=None):
        raise Exception("Host create failed for address %s" % address)

    def test_creation_fail(self):
        with mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.create_host_ssh",
            self.create_host_ssh_fail_patch,
        ):

            response = self.api_client.post(
                self.RESOURCE_PATH,
                data={
                    "objects": [
                        {"address": host_name, "server_profile": "/api/server_profile/test_profile/"}
                        for host_name in MockAgentRpc.mock_servers
                    ]
                },
            )
            self.assertHttpBadRequest(response)
            self.assertEqual(ManagedHost.objects.count(), 0)

            content = json.loads(response.content)

            self.assertEqual(len(content["objects"]), len(MockAgentRpc.mock_servers))

            for index, object in enumerate(content["objects"]):
                self.assertEqual(
                    object["error"], "Host create failed for address %s" % MockAgentRpc.mock_servers.keys()[index]
                )
                self.assertNotEqual(object["traceback"], [None])
                self.assertEqual(object["command_and_host"], None)

    @create_host_ssh_patch
    def test_creation_different_profile(self):
        test_sp = ServerProfile(
            name="test",
            ui_name="test UI",
            ui_description="a test description",
            managed=False,
            worker=False,
            ntp=False,
            corosync=False,
            corosync2=False,
            initial_state="monitored",
        )
        test_sp.save()

        response = self.api_client.post(
            self.RESOURCE_PATH, data={"address": "foo", "server_profile": "/api/server_profile/test/"}
        )
        self.assertHttpAccepted(response)
        self.assertEqual(ManagedHost.objects.count(), 1)

        current_profile = ManagedHost.objects.get().server_profile
        self.assertEquals(test_sp.name, current_profile.name)
        self.assertEquals(test_sp.ui_name, current_profile.ui_name)
        self.assertEquals(test_sp.managed, current_profile.managed)

    @create_host_ssh_patch
    def test_profile(self):
        def test_host_contact(*args, **kwargs):
            return Command.objects.create(message="No-op", complete=True)

        with mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.test_host_contact",
            mock.Mock(side_effect=test_host_contact),
        ) as thc:
            # Test a single post.
            for key in MockAgentRpc.mock_servers:
                response = self.api_client.post(
                    "/api/test_host/",
                    data={
                        "address": key,
                        "private_key_passphrase": "Tom",
                        "private_key": "and",
                        "root_password": "jerry",
                    },
                )
                self.assertHttpAccepted(response)
                content = json.loads(response.content)
                self.assertEqual(content["complete"], True)

                thc.assert_called_once_with(address=key, pkey_pw="Tom", pkey="and", root_pw="jerry")
                thc.reset_mock()

            ManagedHost.objects.all().delete()

            # Test a batch post.
            response = self.api_client.post(
                "/api/test_host/",
                data={
                    "objects": [
                        {
                            "address": "foo",
                            "private_key_passphrase": "Tom",
                            "private_key": "and",
                            "root_password": "Jerry",
                        },
                        {
                            "address": "bar",
                            "private_key_passphrase": "Bill",
                            "private_key": "and",
                            "root_password": "Ben",
                        },
                    ]
                },
            )
            self.assertHttpAccepted(response)
            content = json.loads(response.content)
            self.assertEqual(len(content), 1)

            thc.assert_has_calls(
                [
                    mock.call(address="foo", pkey_pw="Tom", pkey="and", root_pw="Jerry"),
                    mock.call(address="bar", pkey_pw="Bill", pkey="and", root_pw="Ben"),
                ]
            )

    def test_host_validation_single(self):
        def mock_test_host_contact(address, root_pw, pkey, pkey_pw):
            return Command.objects.create(message="Mock Test Host Contact", complete=True)

        with mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.test_host_contact",
            mock.Mock(side_effect=mock_test_host_contact),
        ) as thc:
            # Test a single post.
            for address in MockAgentRpc.mock_servers:
                response = self.api_client.post("/api/test_host/", data={"address": address})
                self.assertHttpAccepted(response)
                content = json.loads(response.content)
                self.assertEqual(content["complete"], True)

            self.assertEqual(thc.call_count, len(MockAgentRpc.mock_servers))

    def test_host_validation_bulk(self):
        def mock_test_host_contact(address, root_pw, pkey, pkey_pw):
            return Command.objects.create(message="Mock Test Host Contact", complete=True)

        with mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.test_host_contact",
            mock.Mock(side_effect=mock_test_host_contact),
        ) as thc:
            response = self.api_client.post(
                "/api/test_host/", data={"objects": [{"address": [address]} for address in MockAgentRpc.mock_servers]}
            )
            self.assertHttpAccepted(response)
            content = json.loads(response.content)

            self.assertEqual(len(content["objects"]), len(MockAgentRpc.mock_servers))
            self.assertEqual(thc.call_count, len(MockAgentRpc.mock_servers))

            for object in content["objects"]:
                self.assertEqual(object["error"], None)
                self.assertEqual(object["traceback"], None)
                self.assertEqual(object["command"]["complete"], True)

    @create_host_ssh_patch
    def _create_hosts_and_validation_profiles(self, validations):
        profile = ServerProfile(
            name="test_profile_2",
            ui_name="Not Test Profile",
            ui_description="Not Test Profile",
            managed=False,
            worker=False,
            corosync=False,
            corosync2=False,
            ntp=False,
            user_selectable=False,
            initial_state="monitored",
        )
        profile.save()

        for profile in ServerProfile.objects.all():
            for validation in validations:
                x = ServerProfileValidation(**validation)
                profile.serverprofilevalidation_set.add(x, bulk=False)
                x.save()

        response = self.api_client.post(
            self.RESOURCE_PATH,
            data={
                "objects": [
                    {"address": host_name, "server_profile": "/api/server_profile/test_profile_2/"}
                    for host_name in MockAgentRpc.mock_servers
                ]
            },
        )

        self.assertHttpAccepted(response)
        content = json.loads(response.content)

        self.assertEqual(len(content["objects"]), len(MockAgentRpc.mock_servers))

        for object in content["objects"]:
            self.assertEqual(object["error"], None)
            self.assertEqual(object["traceback"], None)
            self.assertEqual(object["command_and_host"].keys(), ["host", "command"])

        hosts = ManagedHost.objects.all()
        self.assertEqual(hosts[0].server_profile.name, "test_profile_2")

        return hosts


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

    def __init__(self, method, username="admin", **kwargs):
        ChromaApiTestCase.__init__(self, method, username=username, **kwargs)

    def setUp(self):
        super(TestCreateHostAPI, self).setUp()

        # Body for a POST to either host or test_host
        self.input_data = {
            "address": "myaddress",
            "auth_type": "existing_keys_choice",
            "server_profile": api.get_resource_uri(ServerProfile.objects.get()),
            "root_password": "secret_pw",
            "private_key": sample_private_key,
            "private_key_passphrase": "secret_key_pw",
        }

    def tearDown(self):
        super(TestCreateHostAPI, self).tearDown()

    def _create_host(self):
        ManagedHost.objects.create(
            state="undeployed",
            address="myaddress",
            nodename="myaddress",
            fqdn="myaddress",
            immutable_state=False,
            install_method=ManagedHost.INSTALL_MANUAL,
        )

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
        with mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.test_host_contact", mock.Mock()
        ) as thc:

            def test_host_contact(*args, **kwargs):
                return Command.objects.create(message="No-op", complete=True)

            thc.side_effect = test_host_contact

            api_resp = self.api_client.post("/api/test_host/", data=self.input_data)

            if accept:
                self.assertHttpAccepted(api_resp)

                thc.assert_called_once_with(
                    **{
                        "address": "myaddress",
                        "root_pw": "secret_pw",
                        "pkey": sample_private_key,
                        "pkey_pw": "secret_key_pw",
                    }
                )
            else:
                self.assertHttpBadRequest(api_resp)

                self.assertEqual(
                    thc.call_count, 0, "test_host_contact called %s != 0 for failing case" % thc.call_count
                )

        # Create object so that on the second time round we check the false case.

    def test_create_host_api_ssh_auth(self):
        """Test POST to /api/host/ results in jobschedulerclient call."""

        with mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.create_host_ssh", mock.Mock()
        ) as chs:
            # Got to return something here for API to dehydrate its response
            def create_host_ssh(*args, **kwargs):
                return synthetic_host(kwargs["address"]), Command.objects.create()

            chs.side_effect = create_host_ssh

            response = self.api_client.post("/api/host/", data=self.input_data)
            self.assertHttpAccepted(response)
            job_scheduler_client.JobSchedulerClient.create_host_ssh.assert_called_once_with(
                **{
                    "address": "myaddress",
                    "server_profile": ServerProfile.objects.get().name,
                    "root_pw": "secret_pw",
                    "pkey": sample_private_key,
                    "pkey_pw": "secret_key_pw",
                }
            )
