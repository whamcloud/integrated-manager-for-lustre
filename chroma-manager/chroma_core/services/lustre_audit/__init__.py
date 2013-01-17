#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import traceback
import sys
from chroma_core.services.lustre_audit.update_scan import UpdateScan
from chroma_core.models import ManagedHost
from chroma_core.services import ChromaService, log_register
from chroma_core.services.queue import AgentRxQueue


log = log_register(__name__)


LUSTRE_DEVICE_PLUGIN = 'lustre'


class LustreAgentRx(AgentRxQueue):
    plugin = LUSTRE_DEVICE_PLUGIN


class Service(ChromaService):
    def run(self):
        self._queue = LustreAgentRx()
        self._queue.purge()
        self._queue.serve(data_callback = self.on_data)

    def on_data(self, fqdn, data):
        try:
            host = ManagedHost.objects.get(fqdn = fqdn)
            UpdateScan().run(host.id, data)
        except Exception:
            log.error("Error handling lustre message: %s", '\n'.join(traceback.format_exception(*(sys.exc_info()))))

    def stop(self):
        self._queue.stop()
