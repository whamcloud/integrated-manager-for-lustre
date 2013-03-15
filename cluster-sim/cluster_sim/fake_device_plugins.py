#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import datetime

from chroma_agent.device_plugins.action_runner import ActionRunnerPlugin
from chroma_agent.device_plugins.syslog import MAX_LOG_LINES_PER_MESSAGE
from chroma_agent.plugin_manager import DevicePlugin, DevicePluginMessageCollection, PRIO_LOW

log = logging.getLogger(__name__)


class BaseFakeLinuxPlugin(DevicePlugin):
    _server = None

    def start_session(self):
        return {
            'mpath': {},
            'lvs': {},
            'devs': self._server._devices.get_nodes(self._server.fqdn),
            'local_fs': {},
            'mds': {},
            'vgs': {}
        }


class FakeLinuxNetworkPlugin(DevicePlugin):
    def start_session(self):
        return [{
            "tx_bytes": "24400222349",
            "name": "eth0",
            "rx_bytes": "1789870413"
        }]

    def update_session(self):
        return self.start_session()


class BaseFakeSyslogPlugin(DevicePlugin):
    _server = None

    def start_session(self):
        return {
            'log_lines': [
                {
                    'source': 'cluster_sim',
                    'severity': 1,
                    'facility': 1,
                    'message': "Lustre: Cluster simulator syslog session start %s %s" % (self._server.fqdn, datetime.datetime.now()),
                    'datetime': datetime.datetime.utcnow().isoformat() + 'Z'
                }
            ]
        }

    def update_session(self):
        messages = self._server.pop_log_messages()
        if messages:
            result = DevicePluginMessageCollection([], priority = PRIO_LOW)
            for i in range(0, len(messages), MAX_LOG_LINES_PER_MESSAGE):
                result.append({
                    'log_lines': messages[i:i + MAX_LOG_LINES_PER_MESSAGE]
                })

            return result


class BaseFakeLustrePlugin(DevicePlugin):
    _server = None

    def start_session(self):
        if self._server.state['lnet_up']:
            nids = self._server.nids
        else:
            nids = None

        mounts = []
        for resource in self._server._cluster.get_running_resources(self._server.nodename):
            mounts.append({
                'device': resource['device_path'],
                'fs_uuid': resource['uuid'],
                'mount_point': resource['mount_point'],
                'recovery_status': {}
            })

        return {
            'resource_locations': self._server._cluster.resource_locations(),
            'lnet_loaded': self._server.state['lnet_loaded'],
            'lnet_nids': nids,
            'capabilities': ['manage_targets'],
            'metrics': {
                'raw': {
                    'node': self._server.get_node_stats(),
                    'lustre': self._server.get_lustre_stats()
                }
            },
            'mounts': mounts,
            'lnet_up': self._server.state['lnet_up'],
            'started_at': datetime.datetime.utcnow().isoformat() + "Z",
            'agent_version': 'dummy'
        }

    def update_session(self):
        return self.start_session()


class BaseFakeCorosyncPlugin(DevicePlugin):

    _server = None

    @staticmethod
    def get_test_message(utc_iso_date_str="2013-01-11T19:04:07+00:00",
                         node_status_list=None):
        """Simulate a message from the Corosync agent plugin

        The plugin currently sends datetime in UTC of the nodes localtime.

        TODO:  If that plugin changes format, this must change too.  Consider
        moving this somewhere that is easier to maintain
        e.g. closer to the actual plugin, since the message is initially
        created there based on data reported by corosync.

        TODO: This method is also in tests/unit/services/test_corosync.py.
        Some effort shoudl be considered to consolidate this, so that both
        tests can use the same source.
        """

        #  First whack up some fake node data based on input infos
        nodes = {}
        if node_status_list is not None:
            for hs in node_status_list:
                node = hs[0]
                status = hs[1] and 'true' or 'false'
                node_dict = {node: {
                    "name": node, "standby": "false",
                    "standby_onfail": "false",
                    "expected_up": "true",
                    "is_dc": "true", "shutdown": "false",
                    "online": status, "pending": "false",
                    "type": "member", "id": node,
                    "resources_running": "0", "unclean": "false"}}
                nodes.update(node_dict)

        #  Second create the message with the nodes and other envelope data.
        message = {"nodes": nodes,
                   "datetime": utc_iso_date_str}

        return message

    def start_session(self):

        #  This fake plugin needs to look at it corosync defined peers of
        #  this fake server and determine
        #  which are online.  This happens in production by shelling out the
        #  call crm_mon --one-shot --as-xml

        #  To simulate this, the _server object which is a FakeServer, must
        #  be able to tell this server what it's peers are.

        #  This implementation looks at ALL the servers in the simulator,
        #  and those ones that are also join'ed in the cluster are online.

        log.debug("cluster nodes:  %s" % self._server._cluster.state['nodes'])

        nodes = [(node_dict['fqdn'], node_dict['online']) for node_dict
                            in self._server._cluster.state['nodes'].values()]

        log.debug("Nodes and state:  %s" % nodes)

        dt = datetime.datetime.utcnow().isoformat()
        message = self.get_test_message(utc_iso_date_str=dt,
                                        node_status_list=nodes)

        log.debug(message)
        return message

    def update_session(self):
        return self.start_session()


class FakeDevicePlugins():
    """
    Fake versions of the device plugins, sending monitoring
    information derived from the simulator state (e.g. corosync
    resource locations come from FakeCluster, lustre target
    statistics come from FakeDevices).
    """
    def __init__(self, server):
        self._server = server

        class FakeLinuxPlugin(BaseFakeLinuxPlugin):
            _server = self._server

        class FakeLustrePlugin(BaseFakeLustrePlugin):
            _server = self._server

        class FakeSyslogPlugin(BaseFakeSyslogPlugin):
            _server = self._server

        class FakeCorosyncPlugin(BaseFakeCorosyncPlugin):
            _server = self._server

        self._classes = {
            'linux': FakeLinuxPlugin,
            'linux_network': FakeLinuxNetworkPlugin,
            'lustre': FakeLustrePlugin,
            'action_runner': ActionRunnerPlugin,
            'syslog': FakeSyslogPlugin,
            'corosync': FakeCorosyncPlugin
        }

    def get_plugins(self):
        return self._classes

    def get(self, name):
        return self._classes[name]
