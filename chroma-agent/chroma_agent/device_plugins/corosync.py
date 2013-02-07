#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import xml.etree.ElementTree as xml
from dateutil.tz import tzutc, tzlocal
from dateutil.parser import parse

from chroma_agent import shell
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import DevicePlugin


class CorosyncPlugin(DevicePlugin):
    """ Agent Plugin to read corosync node health status information

        This plugin will run on all nodes and report about the health of
        all nodes in it's peer group.

        See also the chroma_core/services/corosync

        Node status is reported as a dictionary of host names containing
        all of the possible crm_mon data as attributes:
        { 'node1': {name: attr, name: attr...}
          'node2': {name: attr, name: attr...} }

        datetime is passed in localtime converted to UTC.

        Based on xml output from this version of corosync/pacemaker
        crm --version
        1.1.7-6.el6 (Build 148fccfd5985c5590cc601123c6c16e966b85d14)
    """

    COROSYNC_CONNECTION_FAILURE = ("Connection to cluster failed: "
                               "connection failed")

    # This is the message that crm_mon will report
    # when corosync is not running
    def _parse_crm_as_xml(self, raw):
        """ Parse the crm response

        returns dict of node status or ERROR if corosync is down
        """

        return_dict = {}
        try:
            root = xml.fromstring(raw)
        except xml.ParseError:
            # not xml, might be a known error message
            if  CorosyncPlugin.COROSYNC_CONNECTION_FAILURE in raw:
                return_dict['datetime'] = ''
                return_dict['nodes'] = {}
            else:
                daemon_log.warning("Bad xml from corosync crm_mon:  %s" % raw)
        else:
            #  Got node info, pack it up and return
            tm_str = root.find('summary/last_update').get('time')
            return_dict.update({'datetime': self._convert_utc_datetime(tm_str)})

            nodes = {}
            for node in root.findall("nodes/node"):
                host = node.get("name")
                nodes.update({host: node.attrib})

            return_dict['nodes'] = nodes

        return return_dict

    def _convert_utc_datetime(self, tm_str_local):
        """Convert the local time from str time to utc isoformat"""

        dt = parse(tm_str_local).replace(
                            tzinfo=tzlocal()).astimezone(tzutc()).isoformat()
        return dt

    def _read_crm__mod_as_xml(self):
        """ Run crm_mon --one-shot --as-xml  and return raw output"""

        crm_command = ['crm_mon', '--one-shot', '--as-xml']
        rc, stdout, stderr = shell.run(crm_command)
        if rc not in [0, 10]:  # 10 Corosync is not running on this node
            raise RuntimeError("Error (%s) running '%s': '%s' '%s'" %
                                      (rc, crm_command, stdout, stderr))
        return stdout

    def start_session(self):
        return self.update_session()

    def update_session(self):
        raw_output = self._read_crm__mod_as_xml()
        dict_status = self._parse_crm_as_xml(raw_output)

        if dict_status:
            return dict_status
