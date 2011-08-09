
from celery.decorators import task, periodic_task

from configure.lib.job import StepPaused

@task()
def run_job_step(step_instance):
    try:
        step_instance.wrap_run()
    except StepPaused:
        # TODO: deal with multiple jobs in the queue at the same time: there are
        # ways that this could get the steps mixed up
        self.retry(step_instance, countdown = STEP_PAUSE_DELAY)

@task()
def increment_test(test_id):
    from configure.models import Test
    test = Test.objects.select_for_update().get(pk = test_id)
    print test.i
    test.i = test.i + 1
    test.save()

