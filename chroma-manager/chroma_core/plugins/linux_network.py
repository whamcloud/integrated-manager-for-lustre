#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import ScopedId
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin

version = 1


class NetworkInterface(resources.Resource):
    class Meta:
        identifier = ScopedId('name')
        charts = [{"title": "Bandwidth", "series": ['rx_bytes', 'tx_bytes']}]

    name = attributes.String()
    rx_bytes = statistics.Counter(units = "Bytes/s")
    tx_bytes = statistics.Counter(units = "Bytes/s")


class LinuxNetwork(Plugin):
    internal = True

    def _linux_update(self, data):
        for iface in data:
            iface_resource, created = self.update_or_create(NetworkInterface, name = iface['name'])
            iface_resource.rx_bytes = iface['rx_bytes']
            iface_resource.tx_bytes = iface['tx_bytes']

    def agent_session_continue(self, host_resource, data):
        self._linux_update(data)

    def agent_session_start(self, host_resource, data):
        self._linux_update(data)
