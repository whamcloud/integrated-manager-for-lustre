#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import traceback
from django.utils import dateparse
from chroma_core.models import Stats
from chroma_core.services import ChromaService, log_register, queue


log = log_register(__name__)


class StatsQueue(queue.ServiceQueue):
    name = 'stats'

    def put(self, samples):
        queue.ServiceQueue.put(self, [(id, str(dt), value) for id, dt, value in samples])


class Service(ChromaService):
    def run(self):
        self.queue = StatsQueue()
        self.queue.purge()
        self.queue.serve(callback=self.insert)

    def insert(self, samples):
        try:
            outdated = Stats.insert((id, dateparse.parse_datetime(dt), value) for id, dt, value in samples)
        except:
            log.error("Error handling stats insert: " + traceback.format_exc())
        else:
            if outdated:
                log.warn("Outdated samples ignored: {0}".format(outdated))

    def stop(self):
        self.queue.stop()
