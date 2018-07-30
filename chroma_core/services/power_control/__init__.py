# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import threading
from chroma_core.services import ChromaService, ServiceThread


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()
        self.threads = []
        self._children_started = threading.Event()
        self._complete = threading.Event()

    def run(self):
        from chroma_core.services.power_control.manager import PowerControlManager
        from chroma_core.services.power_control.monitor_daemon import PowerMonitorDaemon
        from chroma_core.services.power_control.rpc import PowerControlRpc

        super(Service, self).run()

        manager = PowerControlManager()
        monitor_daemon = PowerMonitorDaemon(manager)

        self._rpc_thread = ServiceThread(PowerControlRpc(manager))
        self._monitor_daemon_thread = ServiceThread(monitor_daemon)

        self._rpc_thread.start()
        self._monitor_daemon_thread.start()

        self._children_started.set()
        self._complete.wait()

    def stop(self):
        super(Service, self).stop()

        # Guard against trying to stop after child threads are created, but before they are started.
        self._children_started.wait()

        self.log.info("Stopping...")
        self._rpc_thread.stop()
        self._monitor_daemon_thread.stop()

        self.log.info("Joining...")
        self._rpc_thread.join()
        self._monitor_daemon_thread.join()

        self.log.info("Complete.")

        self._complete.set()
