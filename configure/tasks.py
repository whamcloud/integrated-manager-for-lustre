
from celery.decorators import task

from configure.lib.job import StepPaused, StepAborted, StepDirtyError, StepCleanError

@task()
def run_job(job_id):
    from configure.lib.job import job_log
    from configure.models import Job
    job = Job.objects.get(pk = job_id)

    # This can happen if we lose power after calling mark_complete but before returning,
    # celery will re-call our unfinished task.
    if job.state == 'complete':
        return None

    job = job.downcast()
    steps = job.get_steps()

    restart_from = 0
    if job.started_step:
        job_log.warning("Job %d restarting, started,finished=%s,%s" % (job.id, job.started_step, job.finished_step))
        if job.started_step != job.finished_step:
            if steps[job.started_step].is_idempotent():
                job_log.info("Job %d step %d will be re-run (it is idempotent)" % (job.id, job.started_step))
            else:
                job_log.error("Job %d step %d is dirty and cannot be re-run (it is not idempotent, marking job errored." % (job.id, job.started_step))
                job.mark_complete(errored = True)
        else:
            job_log.info("Job %d will re-start from step %d" % (job.id, job.started_step + 1))

    from django.db import transaction
    @transaction.commit_on_success()
    def mark_start_step(i):
        job.started_step = i
        job.save()

    from django.db import transaction
    @transaction.commit_on_success()
    def mark_finish_step(i):
        job.finish_step = i
        job.save()

    step_index = 0
    while(step_index < len(steps)):
        mark_start_step(step_index)
        klass, args = steps[step_index]
        step = klass(job, args)
        try:
            step.run(args)
            job_log.debug("Job %d step %d successful" % (job.id, step_index))
        except Exception, e:
            job_log.error("Job %d step %d encountered an error" % (job.id, step_index))
            import sys
            import traceback
            exc_info = sys.exc_info()
            job_log.error('\n'.join(traceback.format_exception(*(exc_info or sys.exc_info()))))
            job.mark_complete(errored = True)
            return None

        mark_finish_step(step_index)
        step_index = step_index + 1

    job.mark_complete(errored = False)

    return None
