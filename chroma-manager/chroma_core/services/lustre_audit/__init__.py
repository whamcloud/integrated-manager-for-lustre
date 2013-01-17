#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import traceback
import sys
from chroma_core.services.lustre_audit.update_scan import UpdateScan
from chroma_core.models import ManagedHost
from chroma_core.services import ChromaService, log_register
from chroma_core.services.queue import ServiceQueue


log = log_register(__name__)


class LustreAgentRx(ServiceQueue):
    name = 'agent_lustre_rx'


class Service(ChromaService):
    def run(self):
        self._queue = LustreAgentRx()
        self._queue.purge()
        self._queue.serve(self.on_message)

    def on_message(self, message):
        try:
            fqdn = message['fqdn']
            # Ignore session info and go straight to body, as the lustre
            # plugin just sends a periodic full dump
            data = message['body']

            host = ManagedHost.objects.get(fqdn = fqdn)
            UpdateScan().run(host.id, data)
        except Exception:
            log.error("Error handling lustre message: %s", '\n'.join(traceback.format_exception(*(sys.exc_info()))))

    def stop(self):
        self._queue.stop()
