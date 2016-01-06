import time
import logging

from tests.integration.core.long_polling_testing import LongPollingThread
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class LongPollingTestCase(ChromaIntegrationTestCase):
    def set_long_polling_endpoint(self, endpoint):
        self.long_polling_end_point = LongPollingThread("/api/host/", self)

    def _wait_response_count(self, count):
        self.wait_until_true(lambda: self.long_polling_end_point.response_count == count,
                             error_message=lambda: ('Expected count {0}\n'
                                                    'Actual Count {1}\n'
                                                    'Polling Data {2}').format(count,
                                                                              self.long_polling_end_point.response_count,
                                                                              self.long_polling_end_point))


class TestHostLongPolling(LongPollingTestCase):
    def test_host_long_polling(self):
        """Test long polling for alerts responds correctly."""

        # Add one host
        host = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        # Now start monitoring the endpoint
        self.set_long_polling_endpoint("/api/host/")

        self._wait_response_count(1)

        # Now wait 10 seconds and the the response count should not have changed.
        time.sleep(10)

        self._wait_response_count(1)

        # Stop LNet and the response should change.
        self.remote_operations.stop_lnet(host['fqdn'])

        self._wait_response_count(2)

        # Now exit.
        self.long_polling_end_point.exit = True

        # Need to cause an alert of some sort, or wait for a timeout of long polling, so start Lnet again.
        self.remote_operations.start_lnet(host['fqdn'])
        self._wait_response_count(3)

        self.long_polling_end_point.join()

        self.assertEqual(self.long_polling_end_point.error, None, self.long_polling_end_point.error)


class TestLNetLongPolling(LongPollingTestCase):
    def test_lnet_long_polling(self):
        """Test long polling for alerts responds correctly."""

        # Add one host
        host = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        # Now start monitoring the endpoint
        self.set_long_polling_endpoint("/api/lnet_configuration/")

        self._wait_response_count(1)

        # Now wait 10 seconds and the the response count should not have changed.
        time.sleep(10)

        self._wait_response_count(1)

        # Stop LNet and the response should change.
        self.remote_operations.stop_lnet(host['fqdn'])

        self._wait_response_count(2)

        # Now exit.
        self.long_polling_end_point.exit = True

        # Need to cause an alert of some sort, or wait for a timeout of long polling, so start Lnet again.
        self.remote_operations.start_lnet(host['fqdn'])
        self._wait_response_count(3)

        self.long_polling_end_point.join()

        self.assertEqual(self.long_polling_end_point.error, None, self.long_polling_end_point.error)


class TestLongPollingLocks(LongPollingTestCase):
    def test_long_polling_locks(self):
        """Test long polling is trigger by locks changing."""

        # Add one host
        host = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        # Now start monitoring the endpoint, host locks change when lnet actions occur. Nothing
        # else changes in the host endpoint
        self.set_long_polling_endpoint("/api/host/")

        self._wait_response_count(1)

        # Do an update because this locks the host but makes no others changes.
        self.chroma_manager.post("/api/command/", body={'jobs': [{'class_name': 'UpdateJob',
                                                                  'args': {'host_id': host['id']}}],
                                                        'message': "Test Long Polling Locks"})

        self._wait_response_count(2)

        # To stop races, allow the long polling thread to exit before we start checking
        # It needs an update to exit, so this is just playing safe.
        self.long_polling_end_point.exit = True
        self.long_polling_end_point.join()

        # The locks should be the only change, and hence the thing that triggered the update
        original_host = self.long_polling_end_point.responses[0].json['objects'][0]
        updated_host = self.long_polling_end_point.responses[1].json['objects'][0]

        # lock will be different because it changed, but display_group, available_transitions, available_actions and
        # available_jobs will be different because they are empty if there is a lock. They do not trigger long polling
        # and so are not responsible for the trigger.
        for key in original_host:
            if key in ['locks', 'display_group', 'available_transitions', 'available_actions', 'available_jobs']:
                self.assertNotEqual(original_host[key], updated_host[key])
            else:
                self.assertEqual(original_host[key], updated_host[key])
