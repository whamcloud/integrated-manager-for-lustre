
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from celery.task import task, periodic_task
from datetime import timedelta

from monitor.lib.lustre_audit import audit_log
from monitor.lib.util import timeit
from monitor.metrics import metrics_log
from settings import AUDIT_PERIOD, EMAIL_ALERTS_PERIOD

import settings


@task()
def monitor_exec(monitor_id, counter):
    from configure.models import Monitor
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


@periodic_task(run_every=timedelta(seconds=AUDIT_PERIOD))
def audit_all():
    import settings
    from configure.models import ManagedHost
    if settings.HTTP_AUDIT:
        for host in ManagedHost.objects.all():
            # If host has ever had contact but is not available now
            if not host.monitor.last_success and not host.is_available():
                # Set the HostContactAlert high
                from monitor.models import HostContactAlert
                HostContactAlert.notify(ManagedHost.objects.get(pk = host['id']), True)
    else:
        for host in ManagedHost.objects.all():
            if host.monitor:
                monitor = host.monitor
            else:
                continue

            tasked = monitor.try_schedule()
            if not tasked:
                audit_log.info("audit_all: host %s audit (%d) still in progress" % (monitor.host, monitor.counter))


@periodic_task(run_every=timedelta(seconds=AUDIT_PERIOD))
def parse_log_entries():
    from monitor.lib.systemevents import SystemEventsAudit
    audit_log.info("parse_log_entries: running")
    SystemEventsAudit().parse_log_entries()


@periodic_task(run_every=timedelta(seconds=AUDIT_PERIOD))
def drain_flms_table():
    from monitor.metrics import FlmsDrain
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


@periodic_task(run_every=timedelta(seconds=AUDIT_PERIOD * 180))
@timeit(logger=metrics_log)
def purge_and_optimize_metrics():
    from monitor.metrics import FlmsDrain
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


@periodic_task(run_every=timedelta(seconds=EMAIL_ALERTS_PERIOD))
def mail_alerts():
    from monitor.models import AlertState, AlertEmail

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
    from monitor.models import AlertState, AlertEmail
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
