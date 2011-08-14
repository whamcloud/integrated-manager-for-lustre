
from celery.decorators import task, periodic_task

from configure.lib.job import StepPaused, StepAborted, StepDirtyError, StepCleanError

import settings
from datetime import datetime, timedelta

def complete_orphan_jobs():
    """This task applies timeouts to cover for crashes/bugs which cause
       something to die between putting the DB in a state which expects
       to be advanced by a celery task, and creating the celery task.
       Also covers situation where we lose comms with AMQP backend and
       adding tasks fails, although ideally task-adders should catch
       that exception themselves."""
    from configure.lib.job import job_log

    # The max. time we will allow between a job committing its
    # state as 'tasked' and committing its task_id to the database.
    # TODO: reconcile this vs. whatever timeout celery is using to talk to AMQP
    # TODO: reconcile this vs. whatever timeout django.db is using to talk to MySQL
    grace_period = timedelta(seconds = 60)

    from configure.models import Job
    orphans = Job.objects.filter(state = 'tasked') \
        .filter(task_id = None) \
        .filter(modified_at__lt = datetime.now() - grace_period)
    for job in orphans:
        job_log.error("Job %d found by janitor (tasked by no task_id since %s), marking errored" % (job.id, job.modified_at))
        job.mark_complete(errored = True)

def remove_old_jobs():
    """Avoid an unlimited buildup of Job objects over long periods of time.  Set
       JOB_MAX_AGE to None to have immortal Jobs."""
    from configure.lib.job import job_log

    try:
        from settings import JOB_MAX_AGE
    except ImportError:
        JOB_MAX_AGE = None

    from configure.models import Job
    old_jobs = Job.objects.filter(created_at__lt = datetime.now() - timedelta(seconds = JOB_MAX_AGE))
    if old_jobs.count() > 0:
        job_log.info("Removing %d old Job objects" % old_jobs.count())
        # Jobs cannot be deleted in one go because of intra-job foreign keys
        for j in old_jobs:
            j.delete()

@periodic_task(run_every = timedelta(seconds = settings.JANITOR_PERIOD))
def janitor():
    """Invoke periodic housekeeping tasks"""
    complete_orphan_jobs()
    remove_old_jobs()

@task()
def run_job(job_id):
    from configure.lib.job import job_log
    job_log.debug("Job %d: run_job" % job_id)

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
            job_log.debug("Job %d running step %d" % (job.id, step_index))
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

    job_log.info("Job %d finished %d steps successfully" % (job.id, job.finish_step + 1))
    job.mark_complete(errored = False)

    return None
