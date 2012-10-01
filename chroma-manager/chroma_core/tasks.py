#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import subprocess
from datetime import timedelta

from celery.beat import Scheduler
from celery.task import task, periodic_task
from celery.worker.control import Panel

from chroma_core.lib.lustre_audit import audit_log

import settings


@Panel.register
def close_logs(panel):
    """Celery remote control command to close log files to avoid
    keeping stale handles after rotation.

    This is used in addition to the behaviour of WatchedFileHandlerWithOwner, to ensure files
    are closed even by processes that never write to them (and therefore would
    otherwise never close them)  See HYD-960.
    """
    for logger_name, logger in logging.root.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers:
                if isinstance(handler, logging.WatchedFileHandler):
                    handler.close()


class EphemeralScheduler(Scheduler):
    """A scheduler which does not persist the schedule to disk because
      we only use high frequency things, so its no problem to just start
      from scratch when celerybeat restarts"""
    def setup_schedule(self):
        self.merge_inplace(self.app.conf.CELERYBEAT_SCHEDULE)
        self.install_default_entries(self.schedule)


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def audit_all():
    from chroma_core.models import ManagedHost
    for host in ManagedHost.objects.all():
        # If host has ever had contact but is not available now
        if host.last_contact and not host.is_available():
            # Set the HostContactAlert high
            from chroma_core.models.host import HostContactAlert
            HostContactAlert.notify(host, True)


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def parse_log_entries():
    from chroma_core.lib.systemevents import SystemEventsAudit
    parsed_count = SystemEventsAudit().parse_log_entries()
    if parsed_count:
        audit_log.debug("parse_log_entries: parsed %d lines" % parsed_count)


@periodic_task(run_every=timedelta(seconds=settings.AUDIT_PERIOD))
def prune_database():
    from chroma_core.lib.systemevents import SystemEventsAudit
    pruned_count = SystemEventsAudit().prune_log_entries()
    audit_log.debug("prune_database: pruned %d entries" % pruned_count)


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
            Agent(host).invoke('host-properties')
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
    from django.db.models import Count

    alert_email = AlertEmail.objects.get(pk = id)

    for user in User.objects.annotate(num_subscriptions = Count('alert_subscriptions')).filter(num_subscriptions__gt = 0):
        alert_messages = []
        subscriptions = [s.alert_type for s in user.alert_subscriptions.all()]
        for alert in AlertState.objects.filter(id__in = alert_email.alerts.all(), content_type__in = subscriptions):
            alert_message = "%s %s" % (alert.begin, alert.message())
            if alert.active:
                alert_message += "  Alert state is currently active"
            alert_messages.append(alert_message)

        if settings.EMAIL_HOST and len(alert_messages) > 0:
            message = "New Chroma Alerts:\n" + "\n".join(alert_messages)
            send_mail('New Chroma Server alerts', message, settings.EMAIL_SENDER,
                      [user.email])
