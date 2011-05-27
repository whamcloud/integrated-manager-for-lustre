# Create your views here.

from django.shortcuts import render_to_response
from django.template import RequestContext

from monitor.models import *

def dashboard(request):
    return render_to_response("dashboard.html",
            RequestContext(request, {}))

def dashboard_inner(request):
    try:
        last_audit = Audit.objects.filter(complete = True).latest('id')
        last_audit_time = last_audit.created_at.strftime("%H:%M:%S %Z %z");
    except Audit.DoesNotExist:
        last_audit_time = "never"
        
    return render_to_response("dashboard_inner.html",
            RequestContext(request, {
                "management_targets": ManagementTarget.objects.all(),
                "filesystems": Filesystem.objects.all(),
                "hosts": Host.objects.all(),
                "clients": Client.objects.all(),
                "last_audit_time": last_audit_time
                }))
