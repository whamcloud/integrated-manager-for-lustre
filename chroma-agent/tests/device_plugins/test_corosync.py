import logging
import datetime
import simplejson as json


from chroma_agent.device_plugins.corosync import CorosyncPlugin
from tests.command_capture_testcase import CommandCaptureTestCase

log = logging.getLogger(__name__)

ONLINE, OFFLINE = 'true', 'false'
CMD = ('crm_mon', '--one-shot', '--as-xml')


class patch_timezone(object):
    def __init__(self, offset_hours):
        self._offset = offset_hours * 3600

    def __enter__(self):
        from dateutil.tz import tzlocal
        self._old_std_offset = tzlocal._std_offset
        self._old_dst_offset = tzlocal._dst_offset
        tzlocal._std_offset = datetime.timedelta(seconds = self._offset)
        tzlocal._dst_offset = datetime.timedelta(seconds = self._offset)

    def __exit__(self, *exc_info):
        from dateutil.tz import tzlocal
        tzlocal._std_offset = self._old_std_offset
        tzlocal._dst_offset = self._old_dst_offset


class TestCorosync(CommandCaptureTestCase):
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

        feed_tz = -8
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

        self.add_command(CMD, stdout=crm_one_shot_xml)

        with patch_timezone(feed_tz):
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

        self.add_command(CMD, rc=10, stdout=crm_corosync_down)

        plugin = CorosyncPlugin(None)
        result_dict = plugin.start_session()

        self.assertTrue(isinstance(result_dict['nodes'], dict))
        self.assertEqual(len(result_dict['nodes']), 0)
        self.assertEqual(result_dict['datetime'], '')

    def test_corosync_causes_session_to_reestablish(self):
        """Connecting to crm_mon fails

        Could not establish cib_ro connection: Connection refused rc=107

        This represents any case that is unknown; which is rc: 0, 10.  In this
        case, the response should be treated like an SPI boundary.  This means
        log it and re-raise.  But, raising is what causes the trashing, so
        instead just return None

        see also:  https://jira.hpdd.intel.com/browse/HYD-1914

        """

        #  Simulate crm_mon returning an unexcepted error code
        self.add_command(CMD, rc=107)

        plugin = CorosyncPlugin(None)
        result_dict = plugin.start_session()
        self.assertTrue(result_dict is None)
