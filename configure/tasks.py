
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

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
    # These are jobs which failed between tasking and tasked
    orphans = Job.objects.filter(state = 'tasking') \
        .filter(modified_at__lt = datetime.now() - grace_period)
    for job in orphans:
        job_log.error("Job %d found by janitor (tasking since %s), marking errored" % (job.id, job.modified_at))
        job.mark_complete(errored = True)

    # Once jobs are tasked, if they fail then they will get resumed by celery, with the exception
    # of ones that we call .cancel on, which could die after revoking their tasks in 'cancelling'
    # before they get to 'completing'
    orphans = Job.objects.filter(state = 'cancelling') \
        .filter(modified_at__lt = datetime.now() - grace_period)
    for job in orphans:
        job_log.error("Job %d found by janitor (cancelling since %s), resuming" % (job.id, job.modified_at))
        job.cancel()

    # TODO: refactor Job so that we can neatly call a 'resume from state X'
    # Jobs can reach the 'completing' state within a celery task, in which case they take
    # care of restarting themselves, or from a call into .cancel in which case we might
    # have to restart them.  We can tell the difference because .cancel sets task_id to
    # None when it goes cancelling->completing.
    orphans = Job.objects.filter(state = 'completing') \
        .filter(task_id = None) \
        .filter(modified_at__lt = datetime.now() - grace_period)
    for job in orphans:
        job_log.error("Job %d found by janitor (completing since %s), resuming" % (job.id, job.modified_at))
        job.complete(errored = job.errored, cancelled = job.cancelled)

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

def job_task_health():
    """Check that all jobs which have a task_id set are either really running in
       celery, or have 'complete' set.
       For debug only -- this isn't watertight, it's just to generate messages
       when something might have gone whacko."""
    from configure.models import Job
    from configure.lib.job import job_log
    from django.db.models import Q
    for job in Job.objects.filter(~Q(task_id = None)).filter(~Q(state = 'complete')):
        # This happens either if a crash has occurred and we're waiting for the janitor
        # to clean it up, or if we had a bug.
        task_state = job.task_state()
        if not task_state in ['PENDING', 'STARTED', 'RETRY']:
            job_log.warning("Job %s has state %s task_id %s but task state is %s" % (job.id, job.state, job.task_id, task_state))

            
@periodic_task(run_every = timedelta(seconds = settings.JANITOR_PERIOD))
def janitor():
    """Invoke periodic housekeeping tasks"""
    complete_orphan_jobs()
    remove_old_jobs()
    if settings.DEBUG:
        job_task_health()

@task()
def set_state(content_type, object_id, new_state):
    """content_type: a ContentType natural key tuple
       object_id: the pk of a StatefulObject instance
       new_state: the string of a state in the StatefulObject's states attribute"""
    # This is done in an async task for two reasons:
    #  1. At time of writing, StateManager.set_state's logic is not safe against
    #     concurrent runs that might schedule multiple jobs for the same objects.
    #     Submitting to a single-worker queue is a simpler and more efficient
    #     way of serializing than locking the table in the database, as we don't
    #     exclude workers from setting there completion and advancing the queue
    #     while we're scheduling new jobs.
    #  2. Calculating the dependencies of a new state is not trivial, because operation
    #     may have thousands of dependencies (think stopping a filesystem with thousands
    #     of OSTs).  We want views like those that create+format a target to return
    #     snappily.
    #
    #  nb. there is an added bonus that StateManager uses some cached tables
    #      built from introspecting StatefulObject and StateChangeJob classes,
    #      and a long-lived worker process keeps those in memory for you.

    from django.contrib.contenttypes.models import ContentType
    model_klass = ContentType.objects.get_by_natural_key(*content_type).model_class()
    instance = model_klass.objects.get(pk = object_id).downcast()

    from configure.lib.state_manager import StateManager
    StateManager()._set_state(instance, new_state)

@task()
def run_job(job_id):
    from configure.lib.job import job_log
    job_log.info("Job %d: run_job" % job_id)

    from configure.models import Job
    job = Job.objects.get(pk = job_id)

    # This can happen if we lose power after calling .complete but before returning,
    # celery will re-call our unfinished task.  Everything has already been done, so
    # just return to let celery drop the task.
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
                job.complete(errored = True)
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
            job.complete(errored = True)
            return None

        mark_finish_step(step_index)
        step_index = step_index + 1

    job_log.info("Job %d finished %d steps successfully" % (job.id, job.finish_step + 1))
    job.complete(errored = False)

    return None
