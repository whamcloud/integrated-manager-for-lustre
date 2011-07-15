
# Create your views here.

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest

from monitor.models import *
from monitor.lib.graph_helper import load_graph,dyn_load_graph

from settings import SYSLOG_PATH

def sparkline_data(request, name, subdir, graph_type):
    params = request.GET.copy()
    params['size'] = 'sparkline'
    data = dyn_load_graph(subdir, name, graph_type, params)
    return HttpResponse(json.dumps(data), 'application/json')

def dyn_graph_loader(request, name, subdir, graph_type):
    image_data, mime_type = dyn_load_graph(subdir, name, graph_type, request.GET)
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
        # NB this is now the last time *any* host was audited, so doesn't indicate
        # an overall "this all is up to date since X", so maybe shouldn't display it?
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
                "events": Event.objects.all().order_by('-created_at'),
                "alerts": AlertState.objects.filter(active = True).order_by('end'),
                "last_audit_time": last_audit_time
                }))


MONTHS=('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
int_to_month = dict(zip(range(1,13), MONTHS))
month_to_int = dict(zip(MONTHS, range(1,13)))

def get_log_data(display_month, display_day, only_lustre):
    for_date = "%s %2d " % (int_to_month[display_month], display_day)

    matched = False
    log_data = []
    for line in open(SYSLOG_PATH):
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
            # We overshot our date, break.
            if matched:
                break

    log_data.reverse()
    return log_data

def log_viewer(request):
    # get the date of the first line
    try:
        log_file = open(SYSLOG_PATH)
    except IOError:
        return render_to_response('log_viewer.html', RequestContext(request, {
            "error": "Cannot open '%s'.  Check your syslog configuration, or \
modify settings.SYSLOG_PATH." % SYSLOG_PATH}))

    line = log_file.readline()
    try:
        (start_m, start_d, junk) = line.split(None, 2)
    except ValueError:
        return render_to_response('log_viewer.html', RequestContext(request, {
            "error": "File '%s' is empty or malformed." % SYSLOG_PATH}))
    
    # and now the last line
    log_file.seek(-1000, 2)
    for line in log_file.readlines():
        last_line = line
    
    (end_m, end_d, junk) = last_line.split(None, 2)

    display_month = month_to_int[end_m]
    display_day = int(end_d)

    import datetime
    start_month_choices = [(i, datetime.date(1970, i, 1).strftime('%B')) for i in range(1,13)]
    start_day_choices = [(i, "%2d" % i) for i in range(1,31)]

    from django import forms
    class LogViewerForm(forms.Form):
        start_month = forms.ChoiceField(label = "Month",
                initial = "%d" % display_month,
                choices = start_month_choices)
        start_day = forms.ChoiceField(label = "Day",
                initial = "%d" % display_day,
                choices = start_day_choices)
        only_lustre = forms.BooleanField(required = False,
                                         initial = True,
                                         label = "Only Lustre messages?")

    if request.method == 'POST': # If the form has been submitted...
        form = LogViewerForm(request.POST) # A form bound to the POST data

        if form.is_valid(): # All validation rules pass
            display_month = int(form.cleaned_data['start_month'])
            display_day = int(form.cleaned_data['start_day'])
            only_lustre = form.cleaned_data['only_lustre']

            log_data = get_log_data(display_month, display_day, only_lustre)
        else:
            log_data = []

    else:
        form = LogViewerForm() # An unbound form
        log_data = get_log_data(display_month, display_day, form.fields['only_lustre'].initial)

    return render_to_response('log_viewer.html', RequestContext(request, {
                                                 "log_data": log_data,
                                                 "form": form}))
def events(request):
    def type_choices():
        klasses = Event.__subclasses__()
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

def alerts(request):
    alert_set = AlertState.objects.filter(active = True).order_by('end')
    alert_history_set = AlertState.objects.filter(active = False).order_by('end')
    return render_to_response('alerts.html', RequestContext(request, {
        'alerts': alert_set,
        'alert_history': alert_history_set}))

def ajax_exception(fn):
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception,e:
            from django.db import transaction

            # Roll back any active transaction
            if transaction.is_dirty():
                transaction.rollback()

            return HttpResponse(json.dumps({'error': "%s" % e}), mimetype = 'application/json', status=500)

    return wrapped

@ajax_exception
def host(request):
    if request.method != 'POST':
        return HttpResponseBadRequest()

    commit = json.loads(request.POST['commit'])
    address = request.POST['address'].__str__()

    # TODO: let user specify agent path
    host, ssh_monitor = SshMonitor.from_string(address)

    if commit:
        from django.db.utils import IntegrityError
        try:
            host.save()
            ssh_monitor.host = host
            ssh_monitor.save()
        except IntegrityError,e:
            raise RuntimeError("Cannot add '%s', possible duplicate address. (%s)" % (address, e))

        result = {'success': True}
    else:
        from tasks import test_host_contact
        print host, ssh_monitor
        job = test_host_contact.delay(host, ssh_monitor)
        result = {'task_id': job.task_id, 'success': True}

    return HttpResponse(json.dumps(result), mimetype = 'application/json')

