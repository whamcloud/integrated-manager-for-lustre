#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import traceback
import dateutil.parser

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import DateTimeField
from django.db.models.query_utils import Q

from chroma_core.services.job_scheduler.agent_rpc import AgentRpc
from chroma_core.services.job_scheduler.job_scheduler_client import NotificationQueue
from chroma_core.services import ChromaService, ServiceThread, log_register
from chroma_core.models.jobs import Job, Command


log = log_register(__name__)


class QueueHandler(object):
    """Service ModiticationNotificationQueue and call into JobScheduler on message

    """
    def __init__(self, job_scheduler):
        self._queue = NotificationQueue()
        self._job_scheduler = job_scheduler

    def stop(self):
        self._queue.stop()

    def run(self):
        # Disregard any old messages
        self._queue.purge()
        self._queue.serve(self.on_message)

    def on_message(self, message):
        try:
            # Deserialize any datetimes which were serialized for JSON
            deserialized_update_attrs = {}
            model_klass = ContentType.objects.get_by_natural_key(*message['instance_natural_key']).model_class()
            for attr, value in message['update_attrs'].items():
                try:
                    field = [f for f in model_klass._meta.fields if f.name == attr][0]
                except IndexError:
                    # e.g. _id names, they aren't datetimes so ignore them
                    deserialized_update_attrs[attr] = value
                else:
                    if isinstance(field, DateTimeField):
                        deserialized_update_attrs[attr] = dateutil.parser.parse(value)
                    else:
                        deserialized_update_attrs[attr] = value

            log.debug("on_message: %s %s" % (message, deserialized_update_attrs))

            self._job_scheduler.notify(
                message['instance_natural_key'],
                message['instance_id'],
                message['time'],
                deserialized_update_attrs,
                message['from_states']
            )
        except:
            # Log bad messages and continue, swallow the exception to avoid
            # bringing down the whole service
            log.warning("on_message: bad message: %s" % traceback.format_exc())


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()

        self._complete = threading.Event()

    def run(self):
        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpc

        # Cancel anything that's left behind from a previous run
        Command.objects.filter(complete = False).update(complete = True, cancelled = True)
        Job.objects.filter(~Q(state = 'complete')).update(state = 'complete', cancelled = True)

        job_scheduler = JobScheduler()
        self._queue_thread = ServiceThread(QueueHandler(job_scheduler))
        self._rpc_thread = ServiceThread(JobSchedulerRpc(job_scheduler))

        AgentRpc.start()
        self._queue_thread.start()
        self._rpc_thread.start()

        self._complete.wait()

        self.log.info("Cancelling outstanding jobs...")

        # Get a fresh view of the job table
        with transaction.commit_manually():
            transaction.commit()
        for job in Job.objects.filter(~Q(state = 'complete')).order_by('-id'):
            job_scheduler.cancel_job(job.id)

    def stop(self):
        AgentRpc.shutdown()

        self.log.info("Stopping...")
        self._rpc_thread.stop()
        self._queue_thread.stop()

        self.log.info("Joining...")
        self._rpc_thread.join()
        self._queue_thread.join()
        self.log.info("Complete.")

        self._complete.set()
