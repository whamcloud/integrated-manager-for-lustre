
from django.core.management.base import BaseCommand

from chroma_core.models import Command as CommandModel, Job, OpportunisticJob
from django.db.models import Q
import datetime


class Command(BaseCommand):
    help = """Cancels all running jobs and commands.  Stop the Chroma services
before running this."""

    def execute(self, *args, **kwargs):
        # See if there are any running workers
        from celery.task.control import inspect
        from socket import gethostname
        i = inspect([gethostname()])
        active_workers = i.active()
        if active_workers:
            raise RuntimeError("Cannot clear Jobs while workers are running, please stop Chroma services first")

        # Cancel anything that's in a running state
        CommandModel.objects.filter(complete = False).update(complete = True, cancelled = True)
        Job.objects.filter(~Q(state = 'complete')).update(state = 'complete', cancelled = True)
        OpportunisticJob.objects.filter(run = False).update(run = True, run_at = datetime.datetime.now())
