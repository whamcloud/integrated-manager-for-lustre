# Create your views here.

from django.shortcuts import render_to_response
from django.template import RequestContext

from monitor.models import *

def dashboard(request):
    return render_to_response("dashboard.html",
            RequestContext(request, {
                "management_targets": ManagementTarget.objects.all(),
                "filesystems": Filesystem.objects.all(),
                "hosts": Host.objects.all(),
                "clients": Client.objects.all(),
                }))
