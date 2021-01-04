from collections import namedtuple

import mock

from chroma_core.models import Nid
from chroma_core.models import Command
from tests.unit.chroma_core.helpers.mock_agent_rpc import MockAgentRpc
from tests.unit.chroma_core.helpers.synthentic_objects import create_host_ssh_patch
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers.helper import log


def mock_update_nids(nids_data):
    command = Command.objects.create(message="No-op", complete=True)

    return command.id


class TestHostResource(ChromaApiTestCase):
    RESOURCE_PATH = "/api/nid/"

    @create_host_ssh_patch
    def setUp(self):
        super(TestHostResource, self).setUp()

        self.host = {
            "fqdn": "foo.mycompany.com",
            "nodename": "foo.mycompany.com",
            "nids": [Nid.Nid("192.168.0.19", "tcp", 0)],
        }

        MockAgentRpc.mock_servers = {"foo": self.host}

        self.api_post("/api/host/", data={"address": "foo", "server_profile": "/api/server_profile/test_profile/"})
        self._lnetinfo = self._get_lnet_info(self.host)

        # Sanity check.
        self.assertEqual(self._lnetinfo.nids, self._lnetinfo.lnet_configuration["nids"])

        mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.update_nids",
            new=mock.Mock(side_effect=mock_update_nids),
        ).start()

        self.addCleanup(mock.patch.stopall)

    def test_validation_missing(self):
        for missing in ["lnd_type", "lnd_network", "network_interface"]:
            # Now create nids on each interface.
            objects = []
            for lnd_network, interface in enumerate(self._lnetinfo.network_interfaces, start=99):
                log.debug("Checking when %s is missing from lnet info" % missing)
                info = {"lnd_type": "tcp", "lnd_network": lnd_network, "network_interface": interface["resource_uri"]}
                del info[missing]

                objects.append(info)

            # Now post these of values, this will wait for the command to complete.
            response = self.api_post(
                self.RESOURCE_PATH,
                data={"objects": objects},
                assertion_test=lambda self, response: self.assertHttpBadRequest(response),
            )

            self.assertEqual(response, {missing: ["Field %s not present in data" % missing]})

    def test_validation_missing_lnd_type_ok(self):
        log.debug("Checking when lnd_type is missing from lnet info but lnd_network == -1")

        self.api_post(
            self.RESOURCE_PATH,
            data={"lnd_network": -1, "network_interface": self._lnetinfo.network_interfaces[0]["resource_uri"]},
        )

    def test_validation_extra(self):
        objects = []
        for lnd_network, interface in enumerate(self._lnetinfo.network_interfaces, start=99):
            objects.append(
                {
                    "extra": "source",
                    "lnd_type": "tcp",
                    "lnd_network": lnd_network,
                    "network_interface": interface["resource_uri"],
                }
            )

        response = self.api_post(
            self.RESOURCE_PATH,
            data={"objects": objects},
            assertion_test=lambda self, response: self.assertHttpBadRequest(response),
        )

        self.assertEqual(response, {"extra": ["Additional field(s) extra found in data"]})

    def test_lnd_type_good_type(self):
        response = self.api_post(
            self.RESOURCE_PATH,
            data={
                "lnd_type": "tcp",
                "lnd_network": 1,
                "network_interface": self._lnetinfo.network_interfaces[0]["resource_uri"],
            },
        )

        self.assertTrue("command" in response)

    def test_lnd_type_bad_type(self):
        response = self.api_post(
            self.RESOURCE_PATH,
            data={
                "lnd_type": "blop",
                "lnd_network": 1,
                "network_interface": self._lnetinfo.network_interfaces[0]["resource_uri"],
            },
            assertion_test=lambda self, response: self.assertHttpBadRequest(response),
        )

        self.assertEqual(
            response,
            {
                "lnd_type": [
                    u"lnd_type blop not valid for interface %s-%s"
                    % (
                        self._lnetinfo.lnet_configuration["host"]["nodename"],
                        self._lnetinfo.network_interfaces[0]["name"],
                    )
                ]
            },
        )

    LNetInfo = namedtuple("LNetInfo", ("nids", "network_interfaces", "lnet_configuration", "host"))

    def _get_lnet_info(self, host):
        """
        :return: Returns a named tuple of network and lnet configuration or None if lnet configuration is not provided
                 by the version of the manager
        """

        # We fetch the host again so that it's state is updated.
        hosts = self.api_get_list("/api/host/", data={"fqdn": host["fqdn"]})
        self.assertEqual(len(hosts), 1, "Expected a single host to be returned got %s" % len(hosts))
        host = hosts[0]

        lnet_configuration = self.api_get_list(
            "/api/lnet_configuration/", data={"host__id": host["id"], "dehydrate__nids": True, "dehydrate__host": True}
        )

        self.assertEqual(
            len(lnet_configuration),
            1,
            "Expected a single lnet configuration to be returned got %s" % len(lnet_configuration),
        )
        lnet_configuration = lnet_configuration[0]

        network_interfaces = self.api_get_list("/api/network_interface/", data={"host__id": host["id"]})

        nids = self.api_get_list("/api/nid/", data={"lnet_configuration__id": lnet_configuration["id"]})

        log.debug("Fetched Lnet info for %s" % host["fqdn"])
        log.debug("Nid info %s" % nids)
        log.debug("NetworkInterfaces info %s" % network_interfaces)
        log.debug("LNetConfiguration info %s" % lnet_configuration)

        return self.LNetInfo(nids, network_interfaces, lnet_configuration, host)
