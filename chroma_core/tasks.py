
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings
from datetime import datetime, timedelta

from celery.task import task, periodic_task, Task
from django.db import transaction

from chroma_core.lib.agent import AgentException
from chroma_core.lib.util import timeit

from chroma_core.lib.job import job_log
from chroma_core.lib.lustre_audit import audit_log
from chroma_core.lib.metrics import metrics_log


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
            job_log.error("Internal error %s" % e)
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
        .filter(modified_at__lt = datetime.now() - grace_period)
    for job in orphans:
        job_log.error("Job %d found by janitor (tasking since %s), marking errored" % (job.id, job.modified_at))
        job.complete(errored = True)

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


def _remove_old_jobs():
    """Avoid an unlimited buildup of Job objects over long periods of time.  Set
       JOB_MAX_AGE to None to have immortal Jobs."""

    try:
        max_age = settings.JOB_MAX_AGE
    except AttributeError:
        max_age = None

    from chroma_core.models import Job
    old_jobs = Job.objects.filter(created_at__lt = datetime.now() - timedelta(seconds = max_age))
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
def notify_state(content_type, object_id, new_state, from_states):
    from chroma_core.lib.state_manager import StateManager
    StateManager._notify_state(content_type, object_id, new_state, from_states)


@task(base = RetryOnSqlErrorTask)
@timeit(logger=job_log)
def set_state(content_type, object_id, new_state, command_id):
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
    instance = model_klass.objects.get(pk = object_id)

    from chroma_core.lib.state_manager import StateManager
    StateManager()._set_state(instance, new_state, command_id)


@task(base = RetryOnSqlErrorTask)
@timeit(logger=job_log)
def add_job(job):
    from chroma_core.lib.state_manager import StateManager
    StateManager()._add_job(job)


@task(base = RetryOnSqlErrorTask)
@timeit(logger=job_log)
def complete_job(job_id):
    from chroma_core.lib.state_manager import StateManager
    StateManager._complete_job(job_id)


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
            if steps[job.started_step].is_idempotent():
                job_log.info("Job %d step %d will be re-run (it is idempotent)" % (job.id, job.started_step))
            else:
                job_log.error("Job %d step %d is dirty and cannot be re-run (it is not idempotent, marking job errored." % (job.id, job.started_step))
                job.complete(errored = True)
        else:
            job_log.info("Job %d will re-start from step %d" % (job.id, job.started_step + 1))

        # If we're picking up after a previous run crashed, go back and mark
        # any incomplete StepResults as complete.
        job.stepresult_set.filter(state = 'incomplete').update(state = 'crashed')

    @transaction.commit_on_success()
    def mark_start_step(i):
        job.started_step = i
        job.save()

    @transaction.commit_on_success()
    def mark_finish_step(i):
        job.finish_step = i
        job.save()

    step_index = 0
    while(step_index < len(steps)):
        mark_start_step(step_index)
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

            # FIXME: questionable value to pickling the exception here, do we do
            # much with it?
            # Exceptions raised locally are not guaranteed to be picklable
            import pickle
            try:
                pickle.dumps(e)
            except pickle.PicklingError:
                # Unpickleable exception, fall back to a generic exception with a message
                e = RuntimeError(e.message)

            result.exception = e
            result.backtrace = backtrace
            result.state = 'failed'
            result.save()

            return None
        finally:
            result.save()

        mark_finish_step(step_index)
        step_index = step_index + 1

    job_log.info("Job %d finished %d steps successfully" % (job.id, job.finish_step + 1))
    job.complete(errored = False)

    return None


@task()
def monitor_exec(monitor_id, counter):
    from chroma_core.models import Monitor
    monitor = Monitor.objects.get(pk = monitor_id)

    # Conditions indicating that we've restarted or that
    if not (monitor.state in ['tasked', 'tasking']):
        audit_log.warn("Host %s monitor %s (audit %s) found unfinished (crash recovery).  Ending task." % (monitor.host, monitor.id, monitor.counter))
        monitor.update(state = 'idle', task_id = None)
        return
    elif monitor.counter != counter:
        audit_log.warn("Host %s monitor found bad counter %s != %s.  Ending task." % (monitor.host, monitor.counter, counter))
        monitor.update(state = 'idle', task_id = None)
        return

    monitor.update(state = 'started')
    audit_log.debug("Monitor %s started" % monitor.host)
    try:
        from monitor.lib.lustre_audit import UpdateScan
        raw_data = monitor.invoke('update-scan',
                settings.AUDIT_PERIOD * 2)
        UpdateScan().run(monitor.host.pk, raw_data)
    except Exception:
        audit_log.error("Exception auditing host %s" % monitor.host)
        import sys
        import traceback
        exc_info = sys.exc_info()
        audit_log.error('\n'.join(traceback.format_exception(*(exc_info or sys.exc_info()))))

    monitor.update(state = 'idle', task_id = None)
    audit_log.debug("Monitor %s completed" % monitor.host)
    return None


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def audit_all():
    import settings
    from chroma_core.models import ManagedHost
    if settings.HTTP_AUDIT:
        for host in ManagedHost.objects.all():
            # If host has ever had contact but is not available now
            if not host.monitor.last_success and not host.is_available():
                # Set the HostContactAlert high
                from chroma_core.models.alert import HostContactAlert
                HostContactAlert.notify(host, True)
    else:
        for host in ManagedHost.objects.all():
            if host.monitor:
                monitor = host.monitor
            else:
                continue

            tasked = monitor.try_schedule()
            if not tasked:
                audit_log.info("audit_all: host %s audit (%d) still in progress" % (monitor.host, monitor.counter))


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def parse_log_entries():
    from chroma_core.lib.systemevents import SystemEventsAudit
    audit_log.info("parse_log_entries: running")
    SystemEventsAudit().parse_log_entries()


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def drain_flms_table():
    from chroma_core.lib.metrics import FlmsDrain
    import os

    drain = FlmsDrain()
    acquire_lock = lambda: drain.lock(os.getpid())
    query_lock = lambda: drain.query_lock()
    release_lock = lambda: drain.unlock()

    if acquire_lock():
        try:
            drain.run()
            return
        finally:
            release_lock()

    metrics_log.warn("Drain task with pid %d has a lock until %s!" % query_lock())


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD * 180))
@timeit(logger=metrics_log)
def purge_and_optimize_metrics():
    from chroma_core.lib.metrics import FlmsDrain
    from r3d.models import Database
    from django.db import connection
    import os
    import time

    # Run the purge first, outside of a lock.  Some performance hit, but
    # we shouldn't see any deadlocks.  We may need to revisit this if we do.
    metrics_log.info("Pid %d starting R3D purge" % os.getpid())
    for db in Database.objects.all():
        db.purge_cdps()
    metrics_log.info("Pid %d finished R3D purge" % os.getpid())

    # We borrow this lock both to avoid stomping on ourselves but also
    # to avoid contending with a drain operation while we're optimizing.
    drain = FlmsDrain()
    acquire_lock = lambda: drain.lock(os.getpid(), 60 * 5)
    query_lock = lambda: drain.query_lock()
    release_lock = lambda: drain.unlock()

    attempts = 10
    while attempts > 0:
        if acquire_lock():
            try:
                cursor = connection.cursor()
                metrics_log.info("Pid %d starting R3D optimize" % os.getpid())
                cursor.execute('OPTIMIZE TABLE r3d_cdp')
                metrics_log.info("Pid %d finished R3D optimize" % os.getpid())
                return
            finally:
                release_lock()

        attempts -= 1
        time.sleep(1)

    metrics_log.warn("Drain task with pid %d has a lock until %s!" % query_lock())


@task()
def test_host_contact(host):
    import socket
    user, hostname, port = host.ssh_params()

    try:
        addresses = socket.getaddrinfo(hostname, "22", socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP)
        resolve = True
        resolved_address = addresses[0][4][0]
    except socket.gaierror:
        resolve = False

    ping = False
    if resolve:
        from subprocess import call
        ping = (0 == call(['ping', '-c 1', resolved_address]))

    # Don't depend on ping to try invoking agent, could well have
    # SSH but no ping
    agent = False
    if resolve:
        result = host.monitor.invoke('update-scan', timeout = settings.AUDIT_PERIOD * 2)
        if isinstance(result, Exception):
            audit_log.error("Error trying to invoke agent on '%s': %s" % (resolved_address, result))
            agent = False
        else:
            agent = True

    return {
            'address': host.address,
            'resolve': resolve,
            'ping': ping,
            'agent': agent,
            }


@periodic_task(run_every=timedelta(seconds=settings.EMAIL_ALERTS_PERIOD))
def mail_alerts():
    from chroma_core.models.alert import AlertState, AlertEmail

    alerts = AlertState.objects.filter(alertemail = None)
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


@task
def installation(databases, user):
    """Actions requiring greater privileges than the apache user has, to be performed
    after the user has been prompted for database settings

    :param databases: Value for settings.DATABASES
    """

    import subprocess
    import logging
    # NB not setting up a handler because in production
    # celeryd will catch the output for us
    log = logging.getLogger('installation')

    class RsyslogConfig:
        CONFIG_FILE = "/etc/rsyslog.conf"
        SENTINEL = "# Added by hydra-server\n"

        def __init__(self, config_file = None):
            self.config_file = config_file or self.CONFIG_FILE

        def remove(self):
            """Remove our config section from the rsyslog config file, or do
            nothing if our section is not there"""
            rsyslog_lines = open(self.config_file).readlines()
            try:
                config_start = rsyslog_lines.index(self.SENTINEL)
                rsyslog_lines.remove(self.SENTINEL)
                config_end = rsyslog_lines.index(self.SENTINEL)
                rsyslog_lines.remove(self.SENTINEL)
                rsyslog_lines = rsyslog_lines[:config_start] + rsyslog_lines[config_end:]
                open(self.config_file, 'w').write("".join(rsyslog_lines))
            except ValueError:
                # Missing start or end sentinel, cannot remove, ignore
                pass

        def add(self, database, server, user, port = None, password = None):
            #:ommysql:database-server,database-name,database-userid,database-password
            config_lines = []
            config_lines.append(self.SENTINEL)
            config_lines.extend([
                        "$ModLoad imtcp.so\n",
                        "$InputTCPServerRun 514\n",
                        "$ModLoad ommysql\n"])
            if port:
                config_lines.append("$ActionOmmysqlServerPort %d\n" % port)

            action_line = "*.*       :ommysql:%s,%s,%s" % (server, database, user)
            if password:
                action_line += ",%s" % password
            action_line += "\n"
            config_lines.append(action_line)
            config_lines.append(self.SENTINEL)

            rsyslog = open(self.config_file, 'a')
            rsyslog.writelines(config_lines)

    # Build a local_settings file
    import os
    project_dir = os.path.dirname(os.path.realpath(settings.__file__))
    local_settings = os.path.join(project_dir, settings.LOCAL_SETTINGS_FILE)
    local_settings_str = ""
    local_settings_str += "CELERY_RESULT_BACKEND = \"database\"\n"
    local_settings_str += "CELERY_RESULT_DBURI = \"mysql://%s:%s@%s%s/%s\"\n" % (
            databases['default']['USER'],
            databases['default']['PASSWORD'],
            databases['default']['HOST'] or "localhost",
            ":%d" % databases['default']['PORT'] if databases['default']['PORT'] else "",
            databases['default']['NAME'])

    # Usefully, a JSON dict looks a lot like python
    import json
    local_settings_str += "DATABASES = %s\n" % json.dumps(databases, indent=4).replace("null", "None")

    # Dump local_settings_str to local_settings
    open(local_settings, 'w').write(local_settings_str)

    # TODO: support SERVER_HTTP_URL
    # TODO: support LOG_SERVER_HOSTNAME

    # Now we have our database, we can populate it
    from django.core.management import ManagementUtility
    ManagementUtility(['', 'syncdb', '--noinput', '--migrate']).execute()

    # The database is populated, we can add our user
    user.save()

    log.info("Adding Chroma daemons")
    subprocess.call(['chkconfig', '--add', 'hydra-worker'])
    subprocess.call(['chkconfig', '--add', 'hydra-storage'])
    log.info("Restarting rsyslogd")
    subprocess.call(['service', 'rsyslogd', 'restart'])

    log.info("Starting Chroma daemons")
    subprocess.call(['service', 'hydra-worker', 'start'])
    subprocess.call(['service', 'hydra-storage', 'start'])

    log.info("Restarting Apache")
    subprocess.call(['service', 'httpd', 'restart'])

    # Finally, restart myself
    # Run this in the background so that we can complete our
    # task and allow celeryd to restart this worker
    log.info("Restarting Chroma service daemon (this process)")
    subprocess.Popen(['service', 'chroma-service', 'restart'])

    rsyslog = RsyslogConfig()
    rsyslog.remove()
    rsyslog.add(databases['default']['NAME'],
                databases['default']['HOST'] or 'localhost',
                databases['default']['USER'],
                databases['default']['PORT'] or None,
                databases['default']['PASSWORD'] or None)
