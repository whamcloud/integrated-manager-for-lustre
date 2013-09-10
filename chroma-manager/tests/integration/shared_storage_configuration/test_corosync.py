
import logging

from testconfig import config
from tests.integration.core.chroma_integration_testcase import (
                                                    ChromaIntegrationTestCase)

log = logging.getLogger(__name__)


class TestCorosync(ChromaIntegrationTestCase):
    """Integration tests involving the CorosyncSerivice and DeviceAgent"""
    TEST_SERVERS = config['lustre_servers'][0:2]

    def test_host_goes_down(self):
        """Test that a host going down results in Alerts

        If a node in a cluster appears as OFFLINE to the corosync agent
        plugin, than the service should raise an Alert.

        In addition to raising an Alert the service makes an attempt to
        save the ManagedHost.corosync_report_up boolean, but since that is
        not deterministic.  If this test fails, disable those portion of this
        test.
        """
        # Establish baseline for alerts
        start_alerts = self.get_list("/api/alert/", {'active': True,
                                                     'severity': 'WARNING'})

        server_config_1 = self.TEST_SERVERS[0]
        server_config_2 = self.TEST_SERVERS[1]

        # Add two hosts
        self.add_hosts([server_config_1['address'], server_config_2['address']])

        # The first update should have said both were online
        def all_hosts_online():
            hosts = self.get_list("/api/host/")
            return all([host['corosync_reported_up'] for host in hosts])
        self.wait_until_true(all_hosts_online)

        # Check no new ERROR alerts - since nothing should be OFFLINE yet
        alerts = self.get_list("/api/alert/", {'active': True,
                                               'severity': 'WARNING'})
        self.assertListEqual(alerts, start_alerts)

        # Kill the second host
        self.remote_operations.kill_server(server_config_2['fqdn'])

        # Check that hosts status is updated
        def host2_offline():
            host2 = self.get_list("/api/host/",
                                  args={'fqdn': server_config_2['fqdn']})[0]
            return host2['corosync_reported_up'] == False
        self.wait_until_true(host2_offline)

        host1 = self.get_list("/api/host/",
                              args={'fqdn': server_config_1['fqdn']})[0]
        self.assertTrue(host1['corosync_reported_up'])

        # Check that an alert was created (be specific to the 'is offline' alert
        # to avoid getting confused by 'lost contact' alerts)
        all_alerts = self.get_list("/api/alert/", {'active': True,
                                                   'severity': 'WARNING'})
        offline_alerts = [a for a in all_alerts if 'is offline' in a['message']]
        self.assertEqual(len(offline_alerts), 1,
                               "%s %s" % (len(all_alerts), len(offline_alerts)))

        # Now start the second host back up
        self.remote_operations.await_server_boot(server_config_2['fqdn'], restart = True)

        # Make sure that host2 eventually goes back to online
        def host2_online():
            host2 = self.get_list("/api/host/",
                                  args={'fqdn': server_config_2['fqdn']})[0]
            return host2['corosync_reported_up'] == True
        self.wait_until_true(host2_online)
