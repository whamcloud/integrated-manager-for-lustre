
import logging
import time

from testconfig import config
from tests.integration.core.chroma_integration_testcase import (
                                                    ChromaIntegrationTestCase)
from tests.integration.shared_storage_configuration import test_alerting

log = logging.getLogger(__name__)


class TestCorosync(ChromaIntegrationTestCase):
    """Integration tests involving the CorosyncSerivice and DeviceAgent"""

    def test_host_goes_down(self):
        """Test that a host going down results in Alerts

        If a node in a cluster appears as OFFLINE to the corosync agent
        plugin, than the service should raise an Alert.

        In addition to raising an Alert the service makes an attempt to
        save the ManagedHost.corosync_report_up boolean, but since that is
        not deterministic.  If this test fails, disable those portion of this
        test.
        """

        server_config_1 = config['lustre_servers'][0]
        server_config_2 = config['lustre_servers'][1]

        # Add two hosts
        self.add_hosts([server_config_1['address'], server_config_2['address']])

        # Wait long enough for the first update to arrive
        time.sleep(test_alerting.UPDATE_DELAY)

        # The first update should have said both were online
        # COMMENT OUT NEXT 3 LINES IF TEST BECOMES BRITTLE
        hosts = self.get_list("/api/host/")
        for host in hosts:
            self.assertTrue(host['corosync_reported_up'], "for: %s - %s" %
                                 (host['fqdn'], host['corosync_reported_up']))

        # Check there no alerts - since nothing should be OFFLINE yet
        alerts = self.get_list("/api/alert/", {'active': True,
                                               'dismissed': False})
        self.assertListEqual(alerts, [])

        # Kill the second host
        self.remote_operations.kill_server(server_config_2['fqdn'])

        # Wait long enough for the first host to send an
        # updated state saying the second host is offline
        time.sleep(test_alerting.UPDATE_DELAY)

        # Check that hosts status is updated
        # COMMENT OUT NEXT 4 LINES IF TEST BECOMES BRITTLE
        host1 = self.get_list("/api/host/",
                              args={'fqdn': server_config_1['fqdn']})[0]
        host2 = self.get_list("/api/host/",
                              args={'fqdn': server_config_2['fqdn']})[0]
        self.assertTrue(host1['corosync_reported_up'])
        self.assertFalse(host2['corosync_reported_up'])

        # Check that an alert was created (be specific to the 'is offline' alert
        # to avoid getting confused by 'lost contact' alerts)
        all_alerts = self.get_list("/api/alert/", {'active': True,
                                               'dismissed': False})
        offline_alerts = [a for a in all_alerts if 'is offline' in a['message']]
        self.assertEqual(len(offline_alerts), 1,
                               "%s %s" % (len(all_alerts), len(offline_alerts)))
