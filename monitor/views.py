# Create your views here.

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest

from monitor.models import *
from monitor.lib.graph_helper import load_graph,dyn_load_graph

def dyn_graph_loader(request, name, subdir, graph_type, size):
    image_data, mime_type = dyn_load_graph(subdir, name, graph_type, size)
    return HttpResponse(image_data, mime_type)

def graph_loader(request, name, subdir):
    image_data, mime_type = load_graph(name)
    return HttpResponse(image_data, mime_type)

def statistics(request):
    # Limit to hosts which we expect there to be some LMT metrics for
    stat_hosts = list(set([tm.host for tm in TargetMount.objects.filter(target__managementtarget = None)]))
    stat_hosts.sort(lambda i,j: cmp(i.address, j.address))
    return render_to_response("statistics.html",
            RequestContext(request, {
                "management_targets": ManagementTarget.objects.all(),
                "filesystems": Filesystem.objects.all().order_by('name'),
                "hosts": stat_hosts,
                "clients": Client.objects.all(),
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
                "filesystems": Filesystem.objects.all().order_by('name'),
                "hosts": Host.objects.all().order_by('address'),
                "clients": Client.objects.all(),
                "last_audit_time": last_audit_time
                }))

from django import forms

MONTHS=('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

def get_log_data(for_date, only_lustre):
    matched = False
    log_data = []
    for line in open("/var/log/hydra"):
        if line == "":
            break
        if only_lustre and line.find(" Lustre") < 0:
            continue
        if line.startswith(for_date):
            matched = True

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

    log_data.reverse()
    return log_data

def log_viewer(request):
    class LogViewerForm(forms.Form):
        start_month = forms.ChoiceField(label = "Starting Month")
        start_day = forms.ChoiceField(label = "Starting Day")
        only_lustre = forms.BooleanField(required = False,
                                         label = "Only Lustre messages?")

    log_file = open("/var/log/hydra")
    # get the date of the first line
    line = log_file.readline()
    (start_m, start_d, junk) = line.split(None, 2)
    
    # and now the last line
    log_file.seek(-1000, 2)
    for line in log_file.readlines():
        last_line = line
    
    (end_m, end_d, junk) = last_line.split(None, 2)
    
    display_month = end_m
    display_day = int(end_d)
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
        form.fields['start_month'].initial = display_month
        form.fields['start_day'].initial = display_day
        form.fields['only_lustre'].initial = only_lustre

        log_data = get_log_data(display_date, only_lustre)
        return render_to_response('log_viewer.html', { 'form': form, },
                                  RequestContext(request,
                                                 { "log_data": log_data, }))

def events(request):
    def type_choices():
        klasses = [HostContactEvent, TargetOnlineEvent, GenericEvent]
        choices = [("", "Any")]
        for klass in klasses:
            choices.append((klass.__name__, klass.type_name()))
        return tuple(choices)

    from django import forms
    class EventFilterForm(forms.Form):
        from logging import INFO, WARNING, ERROR
        host = forms.ModelChoiceField(queryset = Host.objects.all(), empty_label = "Any", required = False)
        severity = forms.ChoiceField((("", "Any"), (INFO, 'info'), (WARNING, 'warning'), (ERROR, 'error')), required = False)
        event_type = forms.ChoiceField(type_choices(), required = False)

    filter_args = []
    filter_kwargs = {}

    if request.method == 'GET':
        form = EventFilterForm()
    elif request.method == 'POST':
        form = EventFilterForm(data = request.POST)
        print form.is_valid()
        print form.errors
        if form.is_valid():
            try:
                host_id = request.POST['host']
                if len(host_id) > 0:
                    filter_kwargs['host'] = host_id
            except:
                pass
            try:
                severity = request.POST['severity']
                if len(severity) > 0:
                    filter_kwargs['severity'] = severity
            except:
                pass
            try:
                klass = request.POST['event_type']
                if len(klass) > 0:
                    from django.db.models import Q
                    klass_lower = klass.lower()
                    filter_args.append(~Q(**{klass_lower: None}))
            except KeyError:
                pass

    event_set = Event.objects.filter(*filter_args, **filter_kwargs).order_by('-created_at')
    return render_to_response('events.html', RequestContext(request, {
        'form': form,
        'events': event_set}))

#def ajax_exception(fn):
#    def wrapped(*args, **kwargs):
#        try:
#            return fn(*args, **kwargs)
#        except Exception,e:
#            return HttpResponse(json.dumps({'error': "%s" % e}), mimetype = 'application/json', status=500)
#
#    return wrapped

def ajax_exception(fn):
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception,e:
            return HttpResponse(json.dumps({'error': "%s" % e}), mimetype = 'application/json', status=500)

    return wrapped

@ajax_exception
def host(request):
    if request.method != 'POST':
        return HttpResponseBadRequest()

    commit = json.loads(request.POST['commit'])
    address = request.POST['address']

    if commit:
        h = Host(address = address)
        from django.db.utils import IntegrityError
        try:
            h.save()
        except IntegrityError,e:
            raise RuntimeError("Cannot add '%s', possible duplicate address. (%s)" % (address, e))

        result = {'success': True}
    else:
        import socket
        try:
            addresses = socket.getaddrinfo(address, "22")
            resolve = True
        except socket.gaierror:
            resolve = False

        ping = False
        if resolve:
            from subprocess import call
            # TODO: sanitize address!!!!! FIXME XXX NO REALLY DO IT!    
            ping = (0 == call(['ping', '-c 1', address]))

        # Don't depend on ping to try invoking agent, could well have 
        # SSH but no ping
        agent = False
        if resolve:
            from monitor.lib.lustre_audit import AGENT_PATH
            from ClusterShell.Task import task_self, NodeSet
            task = task_self()
            task.shell(AGENT_PATH, nodes = NodeSet.fromlist([address.__str__()]));
            task.resume()
            for o, nodes in task.iter_buffers():
                output = "%s" % o

            import simplejson
            try:
                json.loads(output)
                agent = True
            except simplejson.decoder.JSONDecodeError:
                agent = False
            
        result = {
                'address': address,
                'resolve': resolve,
                'ping': ping,
                'agent': agent,
                }
    return HttpResponse(json.dumps(result), mimetype = 'application/json')

