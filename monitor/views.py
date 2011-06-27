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

import re

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

from django import forms

MONTHS=('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# XXX tsk tsk tsk.  this is a copy of the same function from 
#     monitor/lib/lustre_audit.py
#     we need to build a library of this kind of stuff that everyone
#     can use
def normalize_nid(string):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow 
       direct comparisons between NIDs"""
    if string[-4:] == "@tcp":
        string += "0"

    # remove _ from nids (i.e. @tcp_0 -> @tcp0
    i = string.find("_")
    if i > -1:
        string = string[:i] + string [i + 1:]

    return string

def get_log_data(for_date, only_lustre):

    matched = False
    log_data = []
    for line in open("/tmp/syslog"):
        if line == "":
            break
        if only_lustre and line.find(" Lustre") < 0:
            continue
        if line.startswith(for_date):
            matched = True
            p = re.compile("(\d{1,3}\.){3}\d{1,3}@tcp(_\d+)?")
            i = p.finditer(line)
            for match in i:
                replace = match.group()
                replace = normalize_nid(replace)
                try:
                    line = line.replace(match.group(),
                               Nid.objects.get(nid_string = replace).host.address,
                               1)
                except Nid.DoesNotExist:
                    print "failed to replace " + replace

            if line.find(" LustreError") > -1:
                typ = "lustre_error"
            elif line.find(" Lustre") > -1:
                typ = "lustre"
            else:
                typ = "normal"
            log_data.append((line, typ))
        else:
    	# bail out early
            if matched:
                break

    return log_data

def log_viewer(request):

    class LogViewerForm(forms.Form):
        start_month = forms.ChoiceField(label = "Starting Month")
        start_day = forms.ChoiceField(label = "Starting Day")
        only_lustre = forms.BooleanField(required = False,
                                         label = "Only Lustre messages?")

    log_file = open("/tmp/syslog")
    # get the date of the first line
    line = log_file.readline()
    (start_m, start_d, junk) = line.split(None, 2)
    
    # and now the last line
    log_file.seek(-1000, 2)
    for line in log_file.readlines():
        last_line = line
    
    (end_m, end_d, junk) = last_line.split(None, 2)
    
    display_month = start_m
    display_day = int(start_d)
    display_date = "%s %2d " % (display_month, display_day)

    if request.method == 'POST': # If the form has been submitted...
        form = LogViewerForm(request.POST) # A form bound to the POST data
        form.fields['start_month'].choices.append(("6", "Jun"))
        for day in range(int(start_d), int(end_d) + 1):
            form.fields['start_day'].choices.append((day, day))
        #form.fields['only_lustre'].initial = only_lustre
        if form.is_valid(): # All validation rules pass
            only_lustre = True
            display_month = form.cleaned_data['start_month']
            display_day = form.cleaned_data['start_day']
            only_lustre = form.cleaned_data['only_lustre']
            display_date = "%s %2d" % (MONTHS[int(display_month) - 1],
                                       int(display_day))

            log_data = get_log_data(display_date, only_lustre)
        else:
            print "form validation failed"
            log_data = []
        return render_to_response('log_viewer.html', { 'form': form, },
                                      RequestContext(request,
                                                     { "log_data": log_data, }))
    else:
        only_lustre = True
        form = LogViewerForm() # An unbound form
        form.fields['start_month'].choices.append(("6", "Jun"))
        for day in range(int(start_d), int(end_d) + 1):
            form.fields['start_day'].choices.append((day, day))
        form.fields['only_lustre'].initial = only_lustre

        log_data = get_log_data(display_date, only_lustre)
        return render_to_response('log_viewer.html', { 'form': form, },
                                  RequestContext(request,
                                                 { "log_data": log_data, }))
