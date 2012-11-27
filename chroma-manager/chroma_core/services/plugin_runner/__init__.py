#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
from chroma_core.services import ChromaService, ServiceThread
from chroma_core.services.plugin_runner.resource_manager import ResourceManager


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()
        self.threads = []
        self._complete = threading.Event()

    def start(self):
        from chroma_core.services.plugin_runner.agent_daemon import AgentDaemon
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
        from chroma_core.services.plugin_runner.scan_daemon import ScanDaemon
        from chroma_core.services.plugin_runner.scan_daemon_interface import ScanDaemonRpcInterface
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        errors = storage_plugin_manager.get_errored_plugins()
        if errors:
            self.log.error("The following plugins could not be loaded: %s" % errors)
            raise RuntimeError("Some plugins could not be loaded: %s" % errors)

        resource_manager = ResourceManager()
        scan_daemon = ScanDaemon(resource_manager)
        agent_daemon = AgentDaemon(resource_manager)

        scan_daemon_thread = ServiceThread(scan_daemon)
        scan_rpc_thread = ServiceThread(ScanDaemonRpcInterface(scan_daemon))
        agent_rpc_thread = ServiceThread(AgentDaemonRpcInterface(agent_daemon))
        agent_daemon_thread = ServiceThread(agent_daemon)

        self.threads.extend([scan_daemon_thread, agent_daemon_thread, scan_rpc_thread, agent_rpc_thread])
        for thread in self.threads:
            thread.start()

        self._complete.wait()
        self.log.debug("Leaving main loop")

    def stop(self):
        self.log.debug("Stopping...")
        for thread in self.threads:
            thread.stop()
        self.log.debug("Joining...")
        for thread in self.threads:
            thread.join()
        self.log.debug("Done.")
        self._complete.set()
