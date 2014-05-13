from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
import logging
import itertools

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

        self.states = ['lnet_up', 'lnet_down', 'lnet_unloaded']
        self.state_order = itertools.cycle([1, 0, 2, 0, 2, 1, 2, 0, 1, 0, 1, 0, 2, 1, 0, 1, 0, 2, 0, 1, 0, 2, 1, 0, 1, 2, 0, 1, 2, 1, 2, 1, 2, 0, 2, 1, 2, 1, 0, 2, 1, 2, 1, 0])

    def test_nids(self):
        lnetinfo = self._get_lnet_info(self.host)

        # If _get_lnet_info returns None then lnet config is not supported by the version of IML running.
        if not lnetinfo:
            return

        # Sanity check.
        self.assertEqual(lnetinfo.nids, lnetinfo.lnet_configuration['nids'])

        # Now create nids on each interface.
        objects = []
        for lnd_network, interface in enumerate(lnetinfo.network_interfaces, start = 99):
            logger.debug("Setting lnd_network to %s for interface %s" % (lnd_network, interface['name']))
            objects.append({"lnd_network": lnd_network,
                            "network_interface": interface['resource_uri']})

        # Now post these of values, this will wait for the command to complete.
        self.post_by_uri('/api/nid/', {'objects': objects})

        # Now see what we have.
        lnetinfo = self._get_lnet_info(self.host)

        # Sanity check.
        self.assertEqual(lnetinfo.nids, lnetinfo.lnet_configuration['nids'])

        # Check for each position, these are stored in lists and dicts, so try all the positions.
        # at the same time role through the lnet states, the states should persist.
        for lnd_network, nid in enumerate(lnetinfo.nids, start = 999):
            # Now change the nid from to something else
            logger.debug("Setting lnd_network to %s for nid %s" % (lnd_network, lnetinfo.nids[0]['resource_uri']))
            self.set_value(nid['resource_uri'], 'lnd_network', lnd_network, False)

            # Move to another state
            self._change_lnet_state(lnetinfo.lnet_configuration['resource_uri'])

            # Check it worked ok.
            self.assertEqual(self.get_json_by_uri(nid['resource_uri'])['lnd_network'], lnd_network)

            # Now delete the nid
            self.delete_by_uri(nid['resource_uri'])

            # Try fetching it and assert it is not found
            self.wait_for_assert(lambda: self.assertEqual(self.get_by_uri(nid['resource_uri'], False).status_code, 404))

            # We have a valid race condition here. Because the delete doesn't wait for the delete to complete and because we
            # may have seen the nid disappear before all the commands completed. This can occur if asynchronously the new nid
            # status is updated by the regular polling whilst the lnet state is still being manipulated we can request a change
            # of state below that will be cancelled because it is not needed (validly cancelled) so we will just wait for the
            # last command running to complete before we go further.
            # The call below makes sure that the last command has completed, without error.
            self.wait_last_command_complete()

            # Move to another state
            self._change_lnet_state(self.host['resource_uri'])

            # Ensure that the update worked, we have deleted.
            self.assertEqual(len(self._get_lnet_info(self.host).nids), len(lnetinfo.nids) - 1)

            # Now try posting it back.
            self.post_by_uri('/api/nid/', nid)

            # Move to another state
            self._change_lnet_state(lnetinfo.lnet_configuration['resource_uri'])

            # Ensure that the update worked, we have deleted and posted one.
            self.assertEqual(len(self._get_lnet_info(self.host).nids), len(lnetinfo.nids))

            self.assertEqual(lnetinfo.nids, self._get_lnet_info(self.host).nids)

        # Finally and as much so that we leave everything in a nice state for others. Delete the configuration
        # but do this with lnet_unload.
        self.set_state(lnetinfo.lnet_configuration['resource_uri'], 'lnet_unloaded')

        objects = []
        for interface in lnetinfo.network_interfaces:
            logger.debug("Setting lnd_network to %s for interface %s" % (lnd_network, interface['name']))
            objects.append({"lnd_network": -1,
                            "network_interface": interface['resource_uri']})
        self.post_by_uri('/api/nid/', {'objects': objects})

        # Because lnet is not loaded we should see 0 nids.
        self.assertEqual(len(self._get_lnet_info(self.host).nids), 0)

        # But if lnet is up we should receive 1 nid back - because 1 nid is always reported by lnet.
        self.set_state(lnetinfo.lnet_configuration['resource_uri'], 'lnet_up')
        self.assertEqual(len(self._get_lnet_info(self.host).nids), 1)

    def test_lnet_states(self):
        lnetinfo = self._get_lnet_info(self.host)

        # If _get_lnet_info returns None then lnet config is not supported by the version of IML running.
        if not lnetinfo:
            return

        # Just check some state changes
        resource_uris = [lnetinfo.lnet_configuration['resource_uri'], self.host['resource_uri']]

        # Check setting lnet_configuration state and host configuration state reflect however you do it.
        # This code tests that changing lnet configuration via the host is reflected in the lnet_configuration and
        # that vice versa is also true.
        # The inner loop just trys a number of times with each combination.
        for x in range(0, len(resource_uris)):    # 0 is lnet_configuration, 1 is host
            for y in [2, 3]:                      # 2 is lnet_configuration, 3 is host
                for i in range(2):
                    state = self._change_lnet_state(resource_uris[x])
                    self.assertEqual(self._get_lnet_info(self.host)[y]['state'], state)

    def _change_lnet_state(self, object_uri):
        state = self.states[self.state_order.next()]
        self.set_state(object_uri, state)

        return state
