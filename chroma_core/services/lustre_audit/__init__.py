# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import traceback
import sys
from chroma_core.services.lustre_audit.update_scan import UpdateScan
from chroma_core.models import ManagedHost
from chroma_core.services import ChromaService, log_register
from chroma_core.services.queue import AgentRxQueue
from django.db import transaction


log = log_register(__name__)


class Service(ChromaService):
    PLUGIN_NAME = "lustre"

    def __init__(self):
        self._queue = AgentRxQueue(Service.PLUGIN_NAME)
        self._queue.purge()

    def run(self):
        super(Service, self).run()

        self._queue.serve(data_callback=self.on_data)

    def on_data(self, fqdn, data):
        with transaction.commit_manually():
            transaction.commit()

        try:
            host = ManagedHost.objects.get(fqdn=fqdn)
            UpdateScan().run(host.id, data)
        except Exception:
            log.error("Error handling lustre message: %s", "\n".join(traceback.format_exception(*(sys.exc_info()))))

    def stop(self):
        super(Service, self).stop()

        self._queue.stop()
