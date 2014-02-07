from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
import random
import logging

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class TestLNetFunctionality(ChromaIntegrationTestCase):

    def setUp(self):
        self.SIMULATOR_NID_COUNT = 10

        super(TestLNetFunctionality, self).setUp()

        # Create a host with all the bits working.
        self.create_filesystem_simple()

        host = self.get_list("/api/host/", args={'fqdn': self.TEST_SERVERS[0]['fqdn']})
        self.assertEqual(len(host), 1, "Expected a single host to be returned got %s" % len(host))
        self.host = host[0]

    def test_nids(self):

        lnetinfo = self._get_lnet_info(self.host)

        # Sanity check.
        self.assertEqual(lnetinfo.nids, lnetinfo.lnet_configuration['nids'])

        # Now create nids on each interface.
        objects = []
        lnd_network = 99
        for interface in lnetinfo.network_interfaces:
            logger.debug("Setting lnd_network to %s for interface %s" % (lnd_network, interface['name']))
            objects.append({"lnd_network": lnd_network,
                            "network_interface": interface['resource_uri']})
            lnd_network += 1

        # Now post these of values, this will wait for the command to complete.
        self.post_by_uri('/api/nid/', {'objects': objects})

        # Now see what we have.
        lnetinfo = self._get_lnet_info(self.host)

        # Sanity check.
        self.assertEqual(lnetinfo.nids, lnetinfo.lnet_configuration['nids'])

        # Now change the nid from network 0 to network 1
        logger.debug("Setting lnd_network to %s for nid %s" % (1001, lnetinfo.nids[0]['resource_uri']))
        self.set_value(lnetinfo.nids[0]['resource_uri'], 'lnd_network', 1001, False)

        # Check it worked ok.
        self.assertEqual(self.get_json_by_uri(lnetinfo.nids[0]['resource_uri'])['lnd_network'], 1001)

        # Now delete the nid
        self.delete_by_uri(lnetinfo.nids[0]['resource_uri'])

        # Try fetching it and assert it is not found
        self.wait_for_assert(lambda: self.assertEqual(self.get_by_uri(lnetinfo.nids[0]['resource_uri'], False).status_code, 404))

        # Ensure that the update worked, we have deleted.
        self.assertEqual(len(self._get_lnet_info(self.host).nids), len(lnetinfo.nids) - 1)

        # No try posting it back.
        self.post_by_uri('/api/nid/', lnetinfo.nids[0])

        # Ensure that the update worked, we have deleted and posted one.
        self.assertEqual(len(self._get_lnet_info(self.host).nids), len(lnetinfo.nids))

        self.assertEqual(lnetinfo.nids, self._get_lnet_info(self.host).nids)

        # Finally and as much so that we leave everything in a nice state for others. Delete the configuration
        objects = []
        for interface in lnetinfo.network_interfaces:
            logger.debug("Setting lnd_network to %s for interface %s" % (lnd_network, interface['name']))
            objects.append({"lnd_network": -1,
                            "network_interface": interface['resource_uri']})
        self.post_by_uri('/api/nid/', {'objects': objects})

        # So we should no receive 1 nid back - because 1 nid is always reported
        self.assertEqual(len(self._get_lnet_info(self.host).nids), 1)

    def test_lnet_states(self):
        lnetinfo = self._get_lnet_info(self.host)

        # Just check some state changes
        states = ['lnet_up', 'lnet_down', 'lnet_unloaded']
        resource_uris = [lnetinfo.lnet_configuration['resource_uri'], self.host['resource_uri']]

        # Check setting lnet_configuration state and host configuration state reflect however you do it.
        for x in range(0, len(resource_uris)):   # 0 is lnet_configuration, 1 is host
            for y in [2, 3]:                      # 2 is lnet_configuration, 3 is host
                for i in range(0, 2):
                    state = states[random.randrange(0, len(states))]
                    self.set_state(resource_uris[x], state)
                    self.assertEqual(self._get_lnet_info(self.host)[y]['state'], state)
