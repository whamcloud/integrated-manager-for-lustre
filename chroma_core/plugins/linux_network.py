
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.lib.storage_plugin.plugin import StoragePlugin
from chroma_core.lib.storage_plugin.resource import StorageResource, ScannableId

from chroma_core.lib.storage_plugin import attributes, statistics


class NetworkInterface(StorageResource):
    identifier = ScannableId('name')
    name = attributes.String()
    rx_bytes = statistics.Counter()
    tx_bytes = statistics.Counter()


class LinuxNetwork(StoragePlugin):
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
