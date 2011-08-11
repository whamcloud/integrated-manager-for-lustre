
from celery.decorators import task, periodic_task
from datetime import timedelta, datetime

from monitor.lib.lustre_audit import audit_log

@task()
def monitor_exec(monitor_id, audit_id):
    audit_log.debug("monitor_exec: audit %d" % audit_id)
    from monitor.models import Audit, Monitor


    from django.db import transaction
    # Transaction to ensure that 'started' flag is committed before proceeding
    @transaction.commit_on_success
    def mark_begin(audit):
        audit.started = True
        audit.save()
        audit_log.debug("Audit %d marked started" % audit_id)

    # Use 'started' flag to detect whether this is a clean first run 
    audit = Audit.objects.get(pk = audit_id)
    if audit.started:
        audit_log.warn("Audit %d found unfinished (worker crash).  Deleting." % audit_id)
        audit.delete()
        return
    else:
        mark_begin(audit)

    monitor = Monitor.objects.get(pk = monitor_id)
    raw_data = monitor.downcast().invoke()

    success = False
    try:
        from monitor.lib.lustre_audit import LustreAudit
        success = LustreAudit().audit_complete(audit, raw_data)
    finally:
        audit.complete = True
        audit.error = not success
        audit_log.debug("Audit %d marked complete" % audit_id)
        audit.save()

from django.db import transaction
# Transaction to ensure that an Audit doesn't get committed
# without task_id set
@transaction.commit_on_success
def audit_monitor(monitor):
    from monitor.models import Audit
    audit, created = Audit.objects.get_or_create(host = monitor.host, complete = False)
    if not created:
        audit_log.debug("audit_all: host %s audit (%d) still in progress" % (monitor.host, audit.id))
    else:
        from monitor.models import Audit
        async_result = monitor_exec.delay(monitor.id, audit.id)
        audit.task_id = async_result.task_id
        audit.save()

from settings import AUDIT_PERIOD
@periodic_task(run_every=timedelta(seconds=AUDIT_PERIOD))
def audit_all():
    from monitor.models import Monitor
    for monitor in Monitor.objects.all():
        audit_monitor(monitor)

@periodic_task(run_every=timedelta(seconds=AUDIT_PERIOD))
def discover_hosts():
    from monitor.lib.lustre_audit import LustreAudit
    LustreAudit().discover_hosts()

@task()
def test_host_contact(host, ssh_monitor):
    import socket
    try:
        addresses = socket.getaddrinfo(host.address, "22")
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
        try:
            result = ssh_monitor.invoke()
            agent = True
        except ValueError,e:
            print "Error trying to invoke agent on '%s': %s" % (resolved_address, e)
            agent = False
        
    return {
            'address': host.address,
            'resolve': resolve,
            'ping': ping,
            'agent': agent,
            }
