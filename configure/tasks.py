
from celery.decorators import task

from configure.lib.job import StepPaused

@task()
def run_job_step(step_instance):
    try:
        step_instance.wrap_run()
    except StepPaused:
        # TODO: deal with multiple jobs in the queue at the same time: there are
        # ways that this could get the steps mixed up
        self.retry(step_instance, countdown = STEP_PAUSE_DELAY)

