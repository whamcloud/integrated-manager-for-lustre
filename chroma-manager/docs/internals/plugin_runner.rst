
Chroma Manager: Plugin Runner Service
=====================================

There are two somewhat distinct classes which operate within this service:

.. autoclass:: chroma_core.services.plugin_runner.scan_daemon.ScanDaemon

.. autoclass:: chroma_core.services.plugin_runner.agent_daemon.AgentDaemon

AgentDaemon and ScanDaemon run within one process because they share
an instance of ResourceManager, which guards potentially overlapping modifications
of the collection of storage resource records.  In the future, ResourceManager should
be remotely accessible, so that these guys can run in separate processes (HYD-227, HYD-1145

.. autoclass:: chroma_core.services.plugin_runner.resource_manager.ResourceManager

