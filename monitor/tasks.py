
from celery.decorators import task, periodic_task
from datetime import timedelta, datetime

@task()
def monitor_exec(monitor, audit):
    # Record start of audit
    raw_data = monitor.downcast().invoke()

    success = False
    try:
        from monitor.lib.lustre_audit import LustreAudit
        success = LustreAudit().audit_complete(audit, raw_data)
    finally:
        audit.complete = True
        audit.error = not success
        audit.save()

from settings import AUDIT_PERIOD
@periodic_task(run_every=timedelta(seconds=AUDIT_PERIOD))
def audit_all():
    from monitor.models import Host, Audit
    hosts = Host.objects.all()
    for h in hosts:
        monitor = h.monitor

        try:
            open_audit = Audit.objects.get(host = monitor.host, complete = False)
            # The last audit hasn't finished yet
            continue
        except Audit.DoesNotExist:
            # Great, let's start a new one
            pass

        from django.db import transaction

        # Creating an Audit and inserting a monitor_exec job must be 
        # done together in one transaction, to avoid the possibility 
        # of having orphaned incomplete Audits
        @transaction.commit_on_success
        def create_and_exec_audit():
            from monitor.models import Audit
            audit = Audit(complete=False, host = monitor.host)
            audit.save()

            monitor_exec.delay(h.monitor, audit)

        create_and_exec_audit()

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
