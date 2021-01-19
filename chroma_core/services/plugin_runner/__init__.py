# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import threading
from django.db import transaction
from chroma_core.services import ChromaService, ServiceThread
from chroma_core.services.plugin_runner.resource_manager import ResourceManager


class AgentPluginHandlerCollection(object):
    def __init__(self, resource_manager):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.services.plugin_runner.agent_daemon import AgentPluginHandler

        self.resource_manager = resource_manager
        self.handlers = {}
        for plugin_name in storage_plugin_manager.loaded_plugin_names:
            self.handlers[plugin_name] = AgentPluginHandler(resource_manager, plugin_name)

    def setup_host(self, host_id, updates):
        for plugin_name, data in updates.items():
            self.handlers[plugin_name].setup_host(host_id, data)

    def update_host_resources(self, host_id, updates):
        for plugin_name, data in updates.items():
            self.handlers[plugin_name].update_host_resources(host_id, data)

    def remove_host_resources(self, host_id):
        for handler in self.handlers.values():
            handler.remove_host_resources(host_id)

    @transaction.atomic
    def rebalance_host_volumes(self, host_id):
        from chroma_core.models import Volume

        candidates = Volume.objects.filter(volumenode__host__id=host_id).distinct()
        self.resource_manager.balance_unweighted_volume_nodes(candidates)


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()
        self.threads = []
        self._children_started = threading.Event()
        self._complete = threading.Event()

    def run(self):
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
        from chroma_core.services.plugin_runner.scan_daemon import ScanDaemon
        from chroma_core.services.plugin_runner.scan_daemon_interface import ScanDaemonRpcInterface
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        super(Service, self).run()

        errors = storage_plugin_manager.get_errored_plugins()
        if errors:
            self.log.error("The following plugins could not be loaded: %s" % errors)
            raise RuntimeError("Some plugins could not be loaded: %s" % errors)

        resource_manager = ResourceManager()
        scan_daemon = ScanDaemon(resource_manager)

        # For each plugin, start a thread which will consume its agent RX queue
        agent_handlers = AgentPluginHandlerCollection(resource_manager)
        for handler in agent_handlers.handlers.values():
            self.threads.append(ServiceThread(handler))

        scan_daemon_thread = ServiceThread(scan_daemon)
        scan_rpc_thread = ServiceThread(ScanDaemonRpcInterface(scan_daemon))
        agent_rpc_thread = ServiceThread(AgentDaemonRpcInterface(agent_handlers))

        self.threads.extend([scan_daemon_thread, scan_rpc_thread, agent_rpc_thread])
        for thread in self.threads:
            thread.start()

        self._children_started.set()
        self._complete.wait()
        self.log.debug("Leaving main loop")

    def stop(self):
        super(Service, self).stop()

        # Guard against trying to stop after child threads are created, but before they are started.
        self._children_started.wait()

        self.log.debug("Stopping...")
        for thread in self.threads:
            thread.stop()
        self.log.debug("Joining...")
        for thread in self.threads:
            thread.join()
        self.log.debug("Done.")
        self._complete.set()
