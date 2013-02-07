#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

import logging
import simplejson as json

from django.utils import unittest

from chroma_agent.device_plugins.corosync import CorosyncPlugin
from tests.test_utils import patch_run

log = logging.getLogger(__name__)

ONLINE, OFFLINE = 'true', 'false'
CMD = ['crm_mon', '--one-shot', '--as-xml']


class TestCorosync(unittest.TestCase):
    """Assert interfacing with corosync works correctly.

    If the host is up and corosync is responding, then a block of node -> attrs
    should be returned.
    If the host is up and corosync is down, the return {'ERROR': reason }
    """

    def test_corosync_up(self):
        """Check that getting status of corosync works

        The pluging should return something a listing for each node, and time
        it was sourced.

        { 'datetime': now,
          'fqdn1': {name: attr, name: attr...}
          'fqdn2': {name: attr, name: attr...} }

        This plugin is stateless, so there is no enduring state than needs to be
        tested.  The different states of corosync, and different types of return
        values from crm_mon are tested.
        """

        feed_local_datetime = "Fri Jan 11 11:04:07 2013"  # PST  (UTC-8)
        feed_utc_datetime = "2013-01-11T19:04:07+00:00"   # UTC

        # crm_mon --one-shot --as-xml
        # Simulating running this command for output
        # that has two nodes one online one offline.
        crm_one_shot_xml = """<?xml version="1.0"?>
        <crm_mon version="1.1.7-6.el6">
          <summary>
            <last_update time="%s" />
            <last_change time="Thu Jan 10 18:27:14 2013" user=""
                                client="crmd" origin="storage0.node" />
            <stack type="openais" />
            <current_dc present="true"
                version="1.1.7-6.el6-148fccfd5985c5590cc601123c6c16e966b85d14"
                name="storage0.node" id="storage0.node" with_quorum="false" />
            <nodes_configured number="2" expected_votes="2" />
            <resources_configured number="0" />
          </summary>
          <nodes>
            <node name="storage0.node" id="storage0.node" online="true"
                standby="false" standby_onfail="false" pending="false"
                unclean="false" shutdown="false" expected_up="true"
                is_dc="true" resources_running="0" type="member" />
            <node name="storage1.node" id="storage1.node" online="false"
                standby="false" standby_onfail="false" pending="false"
                unclean="false" shutdown="true" expected_up="false"
                is_dc="false" resources_running="0" type="member" />
          </nodes>
          <resources>
          </resources>
        </crm_mon>""" % (feed_local_datetime,)

        with patch_run(expected_args=CMD, stdout=crm_one_shot_xml):

            plugin = CorosyncPlugin(None)
            result_dict = plugin.start_session()

            #  Check it's serializable.
            try:
                json.dumps(result_dict)
            except TypeError:
                self.fail("payload from plugin can't be serialized")

            def check_node(node_name, expected_status):
                tm = result_dict['datetime']
                self.assertEqual(tm, feed_utc_datetime)
                node_record = result_dict['nodes'][node_name]
                self.assertEqual(node_record['name'], node_name)
                self.assertEqual(node_record['online'], expected_status)

            check_node('storage0.node', ONLINE)
            check_node('storage1.node', OFFLINE)

    def test_corosync_down(self):
        """Corosync is not running - attempt was tried, but failed.

        There is no data to return other then an error message

        { 'ERROR':  'Connection to cluster failed: connection failed' }
        """

        #  The result crm_mon will return when corosync is not running.
        crm_corosync_down = """
Connection to cluster failed: connection failed"""

        with patch_run(expected_args=CMD, rc=10, stdout=crm_corosync_down):
            plugin = CorosyncPlugin(None)
            result_dict = plugin.start_session()

            self.assertTrue(isinstance(result_dict['nodes'], dict))
            self.assertEqual(len(result_dict['nodes']), 0)
            self.assertEqual(result_dict['datetime'], '')
