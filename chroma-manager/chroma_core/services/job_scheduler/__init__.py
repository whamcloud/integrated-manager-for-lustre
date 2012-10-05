#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
from chroma_core.services.job_scheduler.job_scheduler_client import ModificationNotificationQueue

from django.db.models.query_utils import Q
from chroma_core.services import ChromaService, ServiceThread


class QueueHandler(object):
    """Service ModiticationNotificationQueue and call into JobScheduler on message

    """
    def __init__(self, job_scheduler):
        self._queue = ModificationNotificationQueue()
        self._job_scheduler = job_scheduler

    def stop(self):
        self._queue.stop()

    def run(self):
        # Disregard any old messages
        self._queue.purge()
        self._queue.serve(self.on_message)

    def on_message(self, message):
        self._job_scheduler.notify_state(
            message['instance_natural_key'],
            message['instance_id'],
            message['time'],
            message['new_state'],
            message['from_states']
        )


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()

        self._complete = threading.Event()

    def start(self):
        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
        from chroma_core.models.jobs import Command, Job
        # Cancel anything that's left behind from a previous run
        Command.objects.filter(complete = False).update(complete = True, cancelled = True)
        Job.objects.filter(~Q(state = 'complete')).update(state = 'complete', cancelled = True)

        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpcInterface

        job_scheduler = JobScheduler()

        self._queue_thread = ServiceThread(QueueHandler(job_scheduler))
        self._queue_thread.start()

        self._rpc_thread = ServiceThread(JobSchedulerRpcInterface(job_scheduler))
        self._rpc_thread.start()

        self._complete.wait()

    def stop(self):
        self.log.info("Stopping...")
        self._rpc_thread.stop()
        self._queue_thread.stop()
        self.log.info("Joining...")
        self._rpc_thread.join()
        self._queue_thread.join()
        self.log.info("Complete.")
        self._complete.set()
