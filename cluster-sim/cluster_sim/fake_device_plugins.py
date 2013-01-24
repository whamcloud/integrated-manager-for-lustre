#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
from chroma_agent.device_plugins.action_runner import ActionRunnerPlugin
from chroma_agent.plugin_manager import DevicePlugin


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
            'messages': [
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
            self._server.log_messages = []
            return {
                'messages': messages
            }


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
            'started_at': datetime.datetime.now().isoformat() + "Z",
            'agent_version': 'dummy'
        }

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

        self._classes = {
            'linux': FakeLinuxPlugin,
            'linux_network': FakeLinuxNetworkPlugin,
            'lustre': FakeLustrePlugin,
            'action_runner': ActionRunnerPlugin,
            'syslog': FakeSyslogPlugin
        }

    def get_plugins(self):
        return self._classes

    def get(self, name):
        return self._classes[name]
