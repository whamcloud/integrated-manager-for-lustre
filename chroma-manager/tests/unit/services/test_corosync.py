#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

import logging

from django.test import TestCase
from chroma_core.models import ManagedHost, HostOfflineAlert
from chroma_core.services.corosync import Service as CorosyncService

log = logging.getLogger(__name__)

ONLINE = 'true'
OFFLINE = 'false'


class CorosyncTestCase(TestCase):

    @staticmethod
    def get_test_message(utc_iso_date_str="2013-01-11T19:04:07+00:00",
                         node_status_list=None):
        """Simulate a message from the Corosync agent plugin

        The plugin currently sends datetime in UTC of the nodes localtime.

        If that plugin changes format, this must change too.  Consider
        moving this somewhere that is easier to maintain
        e.g. closer to the plugin, since the message is initially created there
        based on data reported by corosync.
        """

        #  First whack up some fake node data based on input infos
        nodes = {}
        if node_status_list is not None:
            for hs in node_status_list:
                node = hs[0]
                status = hs[1]  # 'true' or 'false'
                node_dict = {node.nodename: {
                                "name": node.nodename, "standby": "false",
                                "standby_onfail": "false",
                                "expected_up": "true",
                                "is_dc": "true", "shutdown": "false",
                                "online": status, "pending": "false",
                                "type": "member", "id": node.nodename,
                                "resources_running": "0", "unclean": "false"}}
                nodes.update(node_dict)

        #  Second create the message with the nodes and other envelope data.
        message = {"nodes": nodes,
                   "datetime": utc_iso_date_str}

        return message

    def make_managed_host(self, nodename, domain="example.tld", save=True):
        """Create nodes, or reuse ones that are there already."""

        fqdn = "%s.%s" % (nodename, domain)
        node = ManagedHost(address=nodename,
                           fqdn=fqdn,
                           nodename=nodename)

        if save:
            node.save()

        return node

    def _set_status(self, node, status=False):
        """Alter the Managednode.corosync_report_up value for testing"""

        ManagedHost.objects.filter(pk=node.pk).update(
                                                corosync_reported_up=status)

    def setUp(self):

        #  The object being tested
        self.corosync_service = CorosyncService()


class CorosyncTests(CorosyncTestCase):
    """ Test that receiving messages from the corosync plugin

    Points to test:
    1.  The service remembers the most recent update per node
    2.  The statthe us to the ManagedHosts is saved when status changes
    3.  An alert is sent when the status changes
    """

    def test_basic_online_msg(self):
        """Initial status report

        Both hosts online, first message results in status saved in db.
        No Alerts expected.
        """

        msg_date = "2013-01-11T19:04:07+00:00"
        node1 = self.make_managed_host('node1')
        node2 = self.make_managed_host('node2')
        nodes = ((node1, ONLINE), (node2, ONLINE))

        self.corosync_service.on_data(None,
                                      self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, 0)

    def test_host_goes_offline(self):
        """Host goes offline

        Two messages, first both nodes online, then one goes offline
        Check that db is update, service dict is update with status and date
        and an Alert is raised
        """

        #  Process first msg (see test_first_msg)
        msg_date = "2013-01-11T19:04:07+00:00"
        node1 = self.make_managed_host('node1')
        node2 = self.make_managed_host('node2')
        nodes = ((node1, ONLINE), (node2, ONLINE))
        self.corosync_service.on_data(None,
                                      self.get_test_message(msg_date, nodes))

        #  This point, the host might be showing ONLINE, or still the
        #  default which is OFFLINE - if the DB wasn't updated.

        msg_date = "2013-01-11T19:04:08+00:00"
        nodes = ((node1, ONLINE), (node2, OFFLINE))

        initial_alerts = HostOfflineAlert.objects.count()

        self.corosync_service.on_data(None,
                                      self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, initial_alerts + 1)
        alert = HostOfflineAlert.objects.all()[0]
        self.assertTrue(alert.active, "Got alert, but Not Active")

    def test_second_msg_older_than_first(self):

        #  Process first msg on the 8th minute
        msg_date = "2013-01-11T19:04:07+00:00"
        node1 = self.make_managed_host('node1')
        node2 = self.make_managed_host('node2')
        nodes = ((node1, ONLINE), (node2, OFFLINE))
        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, 1)

        #  Process second message that is dated 1 minute behind - should drop
        #  the message, and leave the alert active
        msg_date = "2013-01-11T18:04:07+00:00"
        nodes = ((node1, ONLINE), (node2, ONLINE))
        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, 1)

        alert_raised = HostOfflineAlert.objects.all()[0]
        self.assertTrue(alert_raised.active, "Should still be Active.")

        #  Server back online - the alert should be inactive.
        msg_date = "2013-01-11T20:04:07+00:00"
        nodes = ((node1, ONLINE), (node2, ONLINE))
        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, 1)

        alert_raised = HostOfflineAlert.objects.all()[0]
        self.assertFalse(alert_raised.active)

    def test_resolve_alert(self):
        """Host status changes.

        Note goes down, then back up.  Make sure that the alert is ended
        when the node recovers.
        """

        #  Process first msg (see test_first_msg)
        msg_date = "2013-01-11T19:04:07+00:00"
        node1 = self.make_managed_host('node1')
        node2 = self.make_managed_host('node2')
        nodes = ((node1, ONLINE), (node2, ONLINE))
        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        #  node it now ONLINE

        msg_date = "2013-01-11T19:05:07+00:00"
        nodes = ((node1, ONLINE), (node2, OFFLINE))

        initial_alerts = HostOfflineAlert.objects.count()

        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, initial_alerts + 1)

        alert = HostOfflineAlert.objects.all()[0]
        self.assertTrue(alert.active, "Got alert, but Not Active")

        msg_date = "2013-01-11T19:06:07+00:00"
        nodes = ((node1, ONLINE), (node2, ONLINE))

        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, initial_alerts + 1)

        alert = HostOfflineAlert.objects.all()[0]
        self.assertFalse(alert.active, "Got alert, but was still active")

    def test_start_offline(self):
        """Host is offline, then flips on.

        Make sure alerts behave correctly - there aren't any.
        """

        #  Process first msg (see test_first_msg)
        msg_date = "2013-01-11T19:06:07+00:00"
        node1 = self.make_managed_host('node1')
        node2 = self.make_managed_host('node2')
        nodes = ((node1, ONLINE), (node2, OFFLINE))

        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        msg_date = "2013-01-11T20:06:07+00:00"
        nodes = ((node1, ONLINE), (node2, ONLINE))

        initial_alerts = HostOfflineAlert.objects.count()
        self.assertEqual(initial_alerts, 1)

        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, 1)

    def test_unknown_peer(self):
        """Host reports a peer that is not a ManagedHost

        Should handled quietly, by dropping the host from any processing.
        """

        #  Process first msg (see test_first_msg)
        msg_date = "2013-01-11T19:06:07+00:00"
        node1 = self.make_managed_host('node1')
        node2 = self.make_managed_host('node2', save=False)
        nodes = ((node1, ONLINE), (node2, OFFLINE))

        self.corosync_service.on_data(None,
                                      self.get_test_message(msg_date, nodes))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, 0)

    def test_corosync_down(self):
        """Agents may report that corosync was unavailable

        Make sure the service gracefully handled this case.
        """

        #  Initially, corosync is up and returns online for two nodes
        msg_date = "2013-01-11T19:06:07+00:00"
        node1 = self.make_managed_host('node1')
        node2 = self.make_managed_host('node2')
        nodes = ((node1, ONLINE), (node2, ONLINE))
        self.corosync_service.on_data(None, self.get_test_message(msg_date, nodes))

        #  No nodes, no time.  Simulates messages state when corosync is down
        self.corosync_service.on_data(None, self.get_test_message('', None))

        alerts_raised = HostOfflineAlert.objects.count()
        self.assertEqual(alerts_raised, 0)
