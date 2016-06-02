#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import threading
import traceback

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import DateTimeField
from django.db.models.query_utils import Q

from chroma_core.services.job_scheduler import job_scheduler_notify
from chroma_core.services import ChromaService, ServiceThread, log_register
from chroma_core.models.jobs import Job
from chroma_core.models.command import Command
from chroma_core.chroma_common.lib.date_time import IMLDateTime


log = log_register(__name__)


class QueueHandler(object):
    """Service ModificationNotificationQueue and call into JobScheduler on message

    """
    def __init__(self, job_scheduler):
        self._queue = job_scheduler_notify.NotificationQueue()
        self._queue.purge()
        self._job_scheduler = job_scheduler

    def stop(self):
        self._queue.stop()

    def run(self):
        # Disregard any old messages
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
                        deserialized_update_attrs[attr] = IMLDateTime.parse(value)
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

        self._children_started = threading.Event()
        self._complete = threading.Event()

    def run(self):
        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpc
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        super(Service, self).run()

        # Cancel anything that's left behind from a previous run
        for command in Command.objects.filter(complete=False):
            command.completed(True, True)
        Job.objects.filter(~Q(state='complete')).update(state='complete', cancelled=True)

        self._job_scheduler = JobScheduler()
        self._queue_thread = ServiceThread(QueueHandler(self._job_scheduler))
        self._rpc_thread = ServiceThread(JobSchedulerRpc(self._job_scheduler))
        self._progress_thread = ServiceThread(self._job_scheduler.progress)
        AgentRpc.start()
        self._queue_thread.start()
        self._rpc_thread.start()
        self._progress_thread.start()

        self._children_started.set()
        self._complete.wait()

        self.log.info("Cancelling outstanding jobs...")

        # Get a fresh view of the job table
        with transaction.commit_manually():
            transaction.commit()
        for job in Job.objects.filter(~Q(state = 'complete')).order_by('-id'):
            self._job_scheduler.cancel_job(job.id)

    def stop(self):
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        super(Service, self).stop()

        # Guard against trying to stop after child threads are created, but before they are started
        self._children_started.wait()

        AgentRpc.shutdown()

        self.log.info("Stopping...")
        self._rpc_thread.stop()
        self._queue_thread.stop()
        self._progress_thread.stop()

        self.log.info("Joining...")
        self._rpc_thread.join()
        self._queue_thread.join()
        self._job_scheduler.join_run_threads()
        self._progress_thread.join()
        self.log.info("Complete.")

        self._complete.set()
