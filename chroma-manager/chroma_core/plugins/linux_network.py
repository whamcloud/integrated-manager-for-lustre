
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import ScopedId
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource

from chroma_core.lib.storage_plugin.base_plugin import BaseStoragePlugin


class NetworkInterface(BaseStorageResource):
    identifier = ScopedId('name')
    name = attributes.String()
    rx_bytes = statistics.Counter(units = "Bytes/s")
    tx_bytes = statistics.Counter(units = "Bytes/s")
    charts = [{"title": "Bandwidth", "series": ['rx_bytes', 'tx_bytes']}]


class LinuxNetwork(BaseStoragePlugin):
    internal = True

    def _linux_update(self, data):
        for iface in data:
            iface_resource, created = self.update_or_create(NetworkInterface, name = iface['name'])
            iface_resource.rx_bytes = iface['rx_bytes']
            iface_resource.tx_bytes = iface['tx_bytes']

    def agent_session_continue(self, host_resource, data):
        self.log.info('session continue')
        self._linux_update(data)

    def agent_session_start(self, host_resource, data):
        self.log.info('session start')
        self._linux_update(data)
