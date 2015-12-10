import time
import logging
import itertools

from tests.integration.core.long_polling_testing import LongPollingThread
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase

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

        # Sanity check.
        self.assertEqual(lnetinfo.nids, lnetinfo.lnet_configuration['nids'])

        # Now create nids on each interface.
        objects = []
        for lnd_network, interface in enumerate(lnetinfo.network_interfaces, start = 99):
            logger.debug("Setting lnd_network to %s for interface %s" % (lnd_network, interface['name']))
            objects.append({"lnd_type": "tcp",
                            "lnd_network": lnd_network,
                            "network_interface": interface['resource_uri']})

        # Now post these values, this will wait for the command to complete.
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
            self.set_value(nid['resource_uri'], 'lnd_network', lnd_network, self.VERIFY_SUCCESS_NO)

            # Move to another state
            self._change_lnet_state()

            # Check it worked ok.
            self.assertEqual(self.get_json_by_uri(nid['resource_uri'])['lnd_network'], lnd_network)

            # Now delete the nid
            self.delete_by_uri(nid['resource_uri'])

            # Try fetching it and assert it is not found
            self.wait_for_assert(lambda: self.assertEqual(self.get_by_uri(nid['resource_uri'], verify_successful=False).status_code, 404))

            # We have a valid race condition here. Because the delete doesn't wait for the delete to complete and because we
            # may have seen the nid disappear before all the commands completed. This can occur if asynchronously the new nid
            # status is updated by the regular polling whilst the lnet state is still being manipulated we can request a change
            # of state below that will be cancelled because it is not needed (validly cancelled) so we will just wait for the
            # last command running to complete before we go further.
            # The call below makes sure the last command has completed, without error.
            self.wait_last_command_complete()

            # Move to another state
            self._change_lnet_state()

            # Ensure that the update worked, we have deleted.
            self.assertEqual(len(self._get_lnet_info(self.host).nids),
                             len(lnetinfo.nids) - 1,
                             self._get_lnet_info(self.host).nids)

            # Now try posting it back.
            self.post_by_uri('/api/nid/', nid)

            # Move to another state
            self._change_lnet_state()

            # Ensure that the update worked, we have deleted and posted one.
            self.assertEqual(len(self._get_lnet_info(self.host).nids), len(lnetinfo.nids))

            self.assertEqual(lnetinfo.nids, self._get_lnet_info(self.host).nids)

        # Finally and as much so that we leave everything in a nice state for others. Delete the configuration
        # but do this with lnet_unload.
        self.set_state(self.host['lnet_configuration'], 'lnet_unloaded')

        objects = []
        for interface in lnetinfo.network_interfaces:
            logger.debug("Setting lnd_network to -1 for interface %s" % interface['name'])
            objects.append({"lnd_network": -1,
                            "network_interface": interface['resource_uri']})
        self.post_by_uri('/api/nid/', {'objects': objects})

        # Because lnet is not loaded we should see 0 nids.
        self.assertEqual(len(self._get_lnet_info(self.host).nids), 0, self._get_lnet_info(self.host))

        # But if lnet is up we should receive 1 nid back - because 1 nid is always reported by lnet.
        self.set_state(self.host['lnet_configuration'], 'lnet_up')
        self.assertEqual(len(self._get_lnet_info(self.host).nids), 1, self._get_lnet_info(self.host))

    def _change_lnet_state(self):
        state = self.states[self.state_order.next()]
        self.set_state(self.host['lnet_configuration'], state)

        return state


class TestLNetLongPolling(ChromaIntegrationTestCase):
    def test_lnet_long_polling(self):
        """Test long polling for alerts responds correctly."""

        # Add one host
        host = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        # Now start monitoring the endpoint
        long_polling_end_point = LongPollingThread("/api/lnet_configuration/", self)

        self.wait_until_true(lambda: long_polling_end_point.response_count == 1)

        # Now wait 10 seconds and the the response count should not have changed.
        time.sleep(10)

        self.assertEqual(long_polling_end_point.response_count, 1)

        # Stop LNet and the response should change.
        self.remote_operations.stop_lnet(host['fqdn'])

        self.wait_until_true(lambda: long_polling_end_point.response_count == 2)

        # Now exit.
        long_polling_end_point.exit = True

        # Need to cause an alert of some sort, or wait for a timeout of long polling, so start Lnet again.
        self.remote_operations.start_lnet(host['fqdn'])
        self.wait_until_true(lambda: long_polling_end_point.response_count == 3)

        long_polling_end_point.join()

        self.assertEqual(long_polling_end_point.error, None, long_polling_end_point.error)
