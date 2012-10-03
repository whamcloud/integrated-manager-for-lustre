#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db.models.query_utils import Q
from chroma_core.services import ChromaService


class Service(ChromaService):
    def start(self):
        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
        from chroma_core.models.jobs import Command, Job
        # Cancel anything that's left behind from a previous run
        Command.objects.filter(complete = False).update(complete = True, cancelled = True)
        Job.objects.filter(~Q(state = 'complete')).update(state = 'complete', cancelled = True)

        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerRpcInterface

        self.server = JobSchedulerRpcInterface(JobScheduler())
        self.server.run()

    def stop(self):
        self.server.stop()
