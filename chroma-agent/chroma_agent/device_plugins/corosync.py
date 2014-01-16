#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import xml.etree.ElementTree as xml
from dateutil.tz import tzutc, tzlocal
from dateutil.parser import parse

from chroma_agent import shell
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import DevicePlugin


try:
    # Python 2.7
    from xml.etree.ElementTree import ParseError
    ParseError  # silence pyflakes
except ImportError:
    # Python 2.6
    from xml.parsers.expat import ExpatError as ParseError


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
        """ Parse the crm_mon response

        returns dict of node status or ERROR if corosync is down
        """

        return_dict = {}
        try:
            root = xml.fromstring(raw)
        except ParseError:
            # not xml, might be a known error message
            if CorosyncPlugin.COROSYNC_CONNECTION_FAILURE in raw:
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

        dt = parse(tm_str_local).replace(tzinfo=tzlocal()).astimezone(tzutc()).isoformat()
        return dt

    def _read_crm_mon_as_xml(self):
        """Run crm_mon --one-shot --as-xml, return raw output or None

        For expected return values (0, 10), return the stdout from output.
        If the return value is unexpected, log a warning, and return None
        """

        crm_command = ['crm_mon', '--one-shot', '--as-xml']
        rc, stdout, stderr = shell.run(crm_command)
        if rc not in [0, 10]:  # 10 Corosync is not running on this node
            daemon_log.warning("rc=%s running '%s': '%s' '%s'" %
                               (rc, crm_command, stdout, stderr))
            stdout = None

        return stdout

    def start_session(self):
        return self.update_session()

    def update_session(self):
        """Respond to poll.  Only return if has valid data"""

        raw_output = self._read_crm_mon_as_xml()
        if raw_output:
            dict_status = self._parse_crm_as_xml(raw_output)

            if dict_status:
                return dict_status
