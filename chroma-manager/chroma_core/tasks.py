#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import subprocess
from celery.beat import Scheduler
from django.contrib.contenttypes.models import ContentType
from chroma_core.lib.state_manager import StateManager
from chroma_core.models.jobs import Command

import settings
from datetime import datetime, timedelta

from celery.task import task, periodic_task, Task
from django.db import transaction

from chroma_core.lib.agent import AgentException
from chroma_core.lib.util import timeit

from chroma_core.lib.job import job_log
from chroma_core.lib.lustre_audit import audit_log


class EphemeralScheduler(Scheduler):
    """A scheduler which does not persist the schedule to disk because
      we only use high frequency things, so its no problem to just start
      from scratch when celerybeat restarts"""
    def setup_schedule(self):
        self.merge_inplace(self.app.conf.CELERYBEAT_SCHEDULE)
        self.install_default_entries(self.schedule)


class RetryOnSqlErrorTask(Task):
    """Because state required to guarantee completion (or recognition of failure) of
    a job is stored in the database, if there is an exception accessing the database
    then we must retry the celery task.  Otherwise, e.g. if the DB is inaccessible
    when recording the completion of a job, we will fail to mark it as complete,
    fail to start any dependents, and stall the whole system forever (HYD-343)"""
    abstract = True
    max_retries = None

    def __init__(self, *args, **kwargs):
        super(RetryOnSqlErrorTask, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        from MySQLdb import ProgrammingError, OperationalError
        try:
            return self.run(*args, **kwargs)
        except (ProgrammingError, OperationalError), e:
            import sys
            import traceback
            exc_info = sys.exc_info()
            trace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            job_log.error("Internal error %s" % trace)
            self.retry(args, kwargs, e, countdown=settings.SQL_RETRY_PERIOD)


def _complete_orphan_jobs():
    """This task applies timeouts to cover for crashes/bugs which cause
       something to die between putting the DB in a state which expects
       to be advanced by a celery task, and creating the celery task.
       Also covers situation where we lose comms with AMQP backend and
       adding tasks fails, although ideally task-adders should catch
       that exception themselves."""

    # The max. time we will allow between a job committing its
    # state as 'tasked' and committing its task_id to the database.
    # TODO: reconcile this vs. whatever timeout celery is using to talk to AMQP
    # TODO: reconcile this vs. whatever timeout django.db is using to talk to MySQL
    grace_period = timedelta(seconds=60)

    from chroma_core.models import Job
    # These are jobs which failed between tasking and tasked
    orphans = Job.objects.filter(state = 'tasking') \
        .filter(modified_at__lt = datetime.utcnow() - grace_period)
    for job in orphans:
        job_log.error("Job %d found by janitor (tasking since %s), marking errored" % (job.id, job.modified_at))
        job.complete(errored = True)

    # Once jobs are tasked, if they fail then they will get resumed by celery, with the exception
    # of ones that we call .cancel on, which could die after revoking their tasks in 'cancelling'
    # before they get to 'completing'
    orphans = Job.objects.filter(state = 'cancelling') \
        .filter(modified_at__lt = datetime.utcnow() - grace_period)
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
        .filter(modified_at__lt = datetime.utcnow() - grace_period)
    for job in orphans:
        job_log.error("Job %d found by janitor (completing since %s), resuming" % (job.id, job.modified_at))
        job.complete(errored = job.errored, cancelled = job.cancelled)


def _remove_old_jobs():
    """Avoid an unlimited buildup of Job objects over long periods of time.  Set
       JOB_MAX_AGE to None to have immortal Jobs."""

    try:
        max_age = settings.JOB_MAX_AGE
    except AttributeError:
        max_age = None

    from chroma_core.models import Job
    old_jobs = Job.objects.filter(created_at__lt = datetime.utcnow() - timedelta(seconds = max_age))
    if old_jobs.count() > 0:
        job_log.info("Removing %d old Job objects" % old_jobs.count())
        # Jobs cannot be deleted in one go because of intra-job foreign keys
        for j in old_jobs:
            j.delete()


def _job_task_health():
    """Check that all jobs which have a task_id set are either really running in
       celery, or have 'complete' set.
       For debug only -- this isn't watertight, it's just to generate messages
       when something might have gone whacko."""
    from chroma_core.models import Job
    from django.db.models import Q

    from celery.task.control import inspect
    from socket import gethostname
    # XXX assuming local worker
    i = inspect([gethostname()])
    active_workers = i.active()
    really_running_tasks = set()
    if active_workers:
        for worker_name, active_tasks in active_workers.items():
            for t in active_tasks:
                really_running_tasks.add(t['id'])
    else:
        job_log.warning("No active workers found!")

    for job in Job.objects.filter(~Q(task_id = None)).filter(~Q(state = 'complete')):
        task_state = job.task_state()
        # This happens if celery managed to ack the task but couldn't update the
        # result, e.g. when we retry on a DB error and the result can't make
        # it to the DB either.
        if task_state == 'STARTED' and not job.task_id in really_running_tasks:
            job_log.warning("Job %s has state %s task_id %s task_state %s but is not in list of active tasks" % (job.id, job.state, job.task_id, task_state))

        # This happens either if a crash has occurred and we're waiting for the janitor
        # to clean it up, or if we had a bug.
        if not task_state in ['PENDING', 'STARTED', 'RETRY']:
            job_log.warning("Job %s has state %s task_id %s but task state is %s" % (job.id, job.state, job.task_id, task_state))


@periodic_task(run_every = timedelta(seconds = settings.JANITOR_PERIOD))
@timeit(logger=job_log)
def janitor():
    """Invoke periodic housekeeping tasks"""
    _complete_orphan_jobs()
    _remove_old_jobs()
    if settings.DEBUG:
        _job_task_health()


@task(base = RetryOnSqlErrorTask)
@timeit(logger=job_log)
def notify_state(content_type, object_id, time, new_state, from_states):
    StateManager._notify_state(content_type, object_id, time, new_state, from_states)


@task(base = RetryOnSqlErrorTask)
def command_run_jobs(job_dicts, message):
    assert(len(job_dicts) > 0)
    jobs = []
    for job in job_dicts:
        job_klass = ContentType.objects.get_by_natural_key('chroma_core', job['class_name'].lower()).model_class()
        jobs.append(job_klass(**job['args']))

    with transaction.commit_on_success():
        command = Command.objects.create(message = message)
        job_log.debug("command_run_jobs: command %s" % command.id)
        for job in jobs:
            StateManager().add_job(job, command)
            job_log.debug("command_run_jobs: job %s" % job.id)
        command.jobs_created = True
        command.save()

    from chroma_core.models import Job
    Job.run_next()

    return command.id


@task(base = RetryOnSqlErrorTask)
def command_set_state(object_ids, message):
    """object_ids must be a list of 3-tuples of CT natural key, object PK, state"""
    # StateManager.set_state is invoked in an async task for two reasons:
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

    with transaction.commit_on_success():
        command = Command.objects.create(message = message)
        for ct_nk, o_pk, state in object_ids:
            model_klass = ContentType.objects.get_by_natural_key(*ct_nk).model_class()
            instance = model_klass.objects.get(pk = o_pk)
            StateManager().set_state(instance, state, command.id)

    from chroma_core.models import Job
    Job.run_next()

    return command.id


@task(base = RetryOnSqlErrorTask)
@timeit(logger=job_log)
def complete_job(job_id):
    from chroma_core.lib.state_manager import StateManager
    StateManager._complete_job(job_id)

    from chroma_core.models import Job
    Job.run_next()


@task(base = RetryOnSqlErrorTask)
def unpaused_job(job_id):
    """Notify that a job was unpaused: advance the queue"""
    from chroma_core.models import Job
    Job.run_next()


@task(base = RetryOnSqlErrorTask)
@timeit(logger=job_log)
def run_job(job_id):
    job_log.info("Job %d: run_job" % job_id)

    from chroma_core.models import Job, StepResult
    job = Job.objects.get(pk = job_id)

    # This can happen if we lose power after calling .complete but before returning,
    # celery will re-call our unfinished task.  Everything has already been done, so
    # just return to let celery drop the task.
    if job.state == 'complete':
        return None

    job = job.downcast()
    try:
        steps = job.get_steps()
    except Exception, e:
        job_log.error("Job %d run_steps encountered an error" % (job.id))
        import sys
        import traceback
        exc_info = sys.exc_info()
        job_log.error('\n'.join(traceback.format_exception(*(exc_info or sys.exc_info()))))
        job.complete(errored = True)
        return None

    if job.started_step:
        job_log.warning("Job %d restarting, started, finished=%s,%s" % (job.id, job.started_step, job.finished_step))
        if job.started_step != job.finished_step:
            step_klass, step_args = steps[job.started_step]
            if step_klass.idempotent:
                job_log.info("Job %d step %d will be re-run (it is idempotent)" % (job.id, job.started_step))
            else:
                job_log.error("Job %d step %d is dirty and cannot be re-run (it is not idempotent, marking job errored." % (job.id, job.started_step))
                job.complete(errored = True)
        else:
            job_log.info("Job %d will re-start from step %d" % (job.id, job.started_step + 1))

        # If we're picking up after a previous run crashed, go back and mark
        # any incomplete StepResults as complete.
        job.stepresult_set.filter(state = 'incomplete').update(state = 'crashed')

    step_index = 0
    while step_index < len(steps):
        with transaction.commit_on_success():
            job.started_step = step_index
            job.save()
        klass, args = steps[step_index]

        result = StepResult(
                step_klass = klass,
                args = args,
                step_index = step_index,
                step_count = len(steps),
                job = job)
        result.save()

        step = klass(job, args, result)

        try:
            job_log.debug("Job %d running step %d" % (job.id, step_index))
            step.run(args)
            job_log.debug("Job %d step %d successful" % (job.id, step_index))

            result.state = 'success'
        except AgentException, e:
            job_log.error("Job %d step %d encountered an agent error" % (job.id, step_index))
            job.complete(errored = True)

            result.exception = e
            # Don't bother storing the backtrace to invoke_agent, the interesting part
            # is the backtrace inside the AgentException
            result.state = 'failed'
            result.save()

            return None

        except Exception, e:
            job_log.error("Job %d step %d encountered an error" % (job.id, step_index))
            import sys
            import traceback
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            job_log.error(backtrace)
            job.complete(errored = True)

            # Exceptions raised locally are not guaranteed to be picklable,
            # so check it before assigning to a PickledObjectField
            import pickle
            try:
                pickle.dumps(e)
            except pickle.PicklingError:
                # Unpickleable exception, fall back to a generic exception with a message
                e = RuntimeError("Unpicklable exception of class %s: %s" % (e.__class__.__name__, e.message))

            result.exception = e
            result.backtrace = backtrace
            result.state = 'failed'
            result.save()

            return None
        finally:
            result.save()

        with transaction.commit_on_success():
            job.finish_step = step_index
            job.save()
        step_index += 1

    job_log.info("Job %d finished %d steps successfully" % (job.id, job.finish_step + 1))
    job.complete(errored = False)

    return None


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def audit_all():
    from chroma_core.models import ManagedHost
    for host in ManagedHost.objects.all():
        # If host has ever had contact but is not available now
        if host.last_contact and not host.is_available():
            # Set the HostContactAlert high
            from chroma_core.models.alert import HostContactAlert
            HostContactAlert.notify(host, True)


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def parse_log_entries():
    from chroma_core.lib.systemevents import SystemEventsAudit
    parsed_count = SystemEventsAudit().parse_log_entries()
    if parsed_count:
        audit_log.debug("parse_log_entries: parsed %d lines" % parsed_count)


@task()
def test_host_contact(host):
    import socket
    user, hostname, port = host.ssh_params()

    try:
        resolved_address = socket.gethostbyname(hostname)
    except socket.gaierror:
        resolve = False
        ping = False
    else:
        resolve = True
        ping = (0 == subprocess.call(['ping', '-c 1', resolved_address]))

    from chroma_core.lib.agent import Agent
    if settings.SERVER_HTTP_URL:
        import urlparse
        server_host = urlparse.urlparse(settings.SERVER_HTTP_URL).hostname
    else:
        server_host = socket.getfqdn()

    if resolve:
        try:
            rc, out, err = Agent(host).ssh("ping -c 1 %s" % server_host)
        except Exception, e:
            audit_log.error("Error trying to invoke agent on '%s': %s" % (resolved_address, e))
            reverse_resolve = False
            reverse_ping = False
        else:
            if rc == 0:
                reverse_resolve = True
                reverse_ping = True
            elif rc == 1:
                # Can resolve, cannot ping
                reverse_resolve = True
                reverse_ping = False
            else:
                # Cannot resolve
                reverse_resolve = False
                reverse_ping = False
    else:
        reverse_resolve = False
        reverse_ping = False

    # Don't depend on ping to try invoking agent, could well have
    # SSH but no ping
    agent = False
    if resolve:
        try:
            Agent(host).invoke('get-fqdn')
            agent = True
        except Exception, e:
            audit_log.error("Error trying to invoke agent on '%s': %s" % (resolved_address, e))
            agent = False

    return {
            'address': host.address,
            'resolve': resolve,
            'ping': ping,
            'agent': agent,
            'reverse_resolve': reverse_resolve,
            'reverse_ping': reverse_ping
            }


@periodic_task(run_every=timedelta(seconds=settings.EMAIL_ALERTS_PERIOD))
def mail_alerts():
    from chroma_core.models.alert import AlertState, AlertEmail

    alerts = AlertState.objects.filter(alertemail = None, dismissed = False)
    if not alerts:
        # no un-e-mailed alerts yet so just bail
        return

    alert_email = AlertEmail()
    alert_email.save()
    alert_email.alerts.add(*alerts)
    alert_email.save()

    send_alerts_email.delay(id = alert_email.id)


@task()
def send_alerts_email(id):
    from chroma_core.models.alert import AlertState, AlertEmail
    from django.contrib.auth.models import User
    from django.core.mail import send_mail

    alert_email = AlertEmail.objects.get(pk = id)

    # for a recipient:
    for user in User.objects.all():
        message = "New Chroma Alerts:"
        for alert in AlertState.objects.filter(id__in = alert_email.alerts.all()):
            message += "\n%s %s" % (alert.begin, alert.message())
            if alert.active:
                message += "  Alert state is currently active"

        send_mail('New Chroma Server alerts', message, settings.EMAIL_SENDER,
                  [user.email])
