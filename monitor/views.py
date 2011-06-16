# Create your views here.

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse

from monitor.models import *
from monitor.lib.graph_helper import load_graph,dyn_load_graph

def dyn_graph_loader(request, name, subdir, graph_type, size):
    image_data, mime_type = dyn_load_graph(subdir, name, graph_type, size)
    return HttpResponse(image_data, mime_type)

def graph_loader(request, name, subdir):
    image_data, mime_type = load_graph(name)
    return HttpResponse(image_data, mime_type)

def statistics(request):
    return render_to_response("statistics.html",
            RequestContext(request, {
                "management_targets": ManagementTarget.objects.all(),
                "filesystems": Filesystem.objects.all().order_by('name'),
                "hosts": Host.objects.all().order_by('address'),
                "clients": Client.objects.all(),
                }))

def statistics_inner(request):
    try:
        last_audit = Audit.objects.filter(complete = True).latest('id')
        last_audit_time = last_audit.created_at.strftime("%H:%M:%S %Z %z");
    except Audit.DoesNotExist:
        last_audit_time = "never"
        
    return render_to_response("statistics_inner.html",
            RequestContext(request, {
                "management_targets": ManagementTarget.objects.all(),
                "filesystems": Filesystem.objects.all().order_by('name'),
                "hosts": Host.objects.all().order_by('address'),
                "clients": Client.objects.all(),
                "last_audit_time": last_audit_time
                }))

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
