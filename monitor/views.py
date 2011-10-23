
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# Create your views here.

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest

from configure.models import *
from monitor.models import *

from settings import SYSLOG_PATH

def dashboard(request):
    return render_to_response("dashboard.html",
            RequestContext(request, {}))

class Dashboard:
    class StatusItem:
        def __init__(self, dashboard, item):
            self.dashboard = dashboard
            self.item = item

        def status(self):
            return self.dashboard.all_statuses[self.item]

    def __init__(self):
        self.all_statuses = {}
        # 1 query for getting all targetmoun
        for mount in ManagedTargetMount.objects.all():
            # 1 query per targetmount to get any alerts
            self.all_statuses[mount] = mount.status_string()

        from collections import defaultdict
        target_mounts_by_target = defaultdict(list)
        target_mounts_by_host = defaultdict(list)
        target_params_by_target = defaultdict(list)
        for target_klass in ManagedMgs, ManagedMdt, ManagedOst:
            # 1 query to get all targets of a type
            for target in target_klass.objects.all():
                # 1 query per target to get the targetmounts
                target_mounts = target.managedtargetmount_set.all()
                try:
                    target_mountable_statuses = dict(
                            [(m, self.all_statuses[m]) for m in target_mounts])
                except KeyError:
                    continue
                target_mounts_by_target[target].extend(target_mounts)
                for tm in target_mounts:
                    target_mounts_by_host[tm.host_id].append(tm)
                self.all_statuses[target] = target.status_string(target_mountable_statuses)

                target_params_by_target[target] = target.get_params()

        self.filesystems = []
        # 1 query to get all filesystems
        for filesystem in ManagedFilesystem.objects.all().order_by('name'):
            # 3 queries to get targets (of each type)
            targets = filesystem.get_targets()
            try:
                fs_target_statuses = dict(
                        [(t, self.all_statuses[t]) for t in targets])
            except KeyError:
                continue
            self.all_statuses[filesystem] = filesystem.status_string(fs_target_statuses)

            fs_status_item = Dashboard.StatusItem(self, filesystem)
            fs_status_item.targets = []
            for target in targets:
                target_status_item = Dashboard.StatusItem(self, target)
                target_status_item.target_mounts = []
                for tm in target_mounts_by_target[target]:
                    target_mount_status_item = Dashboard.StatusItem(self, tm)
                    target_mount_status_item.target_params = target_params_by_target[target]
                    target_status_item.target_mounts.append(target_mount_status_item)
                fs_status_item.targets.append(target_status_item)

            self.filesystems.append(fs_status_item)

        self.hosts = []
        # 1 query to get all hosts
        for host in ManagedHost.objects.all().order_by('address'):
            host_tms = target_mounts_by_host[host.id]
            # 1 query to get alerts
            host_tm_statuses = dict([(tm, self.all_statuses[tm]) for tm in host_tms])
            self.all_statuses[host] = host.status_string(host_tm_statuses)
            host_status_item = Dashboard.StatusItem(self, host)
            host_status_item.target_mounts = [Dashboard.StatusItem(self, tm) for tm in host_tms]
            self.hosts.append(host_status_item)

def dashboard_inner(request):
    dashboard_data = Dashboard()

    return render_to_response("dashboard_inner.html",
            RequestContext(request, {
                "events": Event.objects.all().order_by('-created_at'),
                "alerts": AlertState.objects.filter(active = True).order_by('end'),
                "dashboard_data": dashboard_data
                }))


def get_log_data(display_month, display_day, only_lustre):
    import datetime

    if display_month == 0:
        start_date = datetime.datetime(1970, 1, 1)
    else:
        start_date = datetime.datetime(datetime.datetime.now().year,
                                       display_month, display_day)
    log_data = []
    log_data = Systemevents.objects.filter(devicereportedtime__gt =
                                           start_date).order_by('-devicereportedtime')

    if only_lustre:
        log_data = log_data.filter(message__startswith=" Lustre")

    return log_data

def log_viewer(request):
    import datetime
    start_month_choices = [(i, datetime.date(1970, i, 1).strftime('%B')) for i in range(1,13)]
    start_day_choices = [(i, "%2d" % i) for i in range(1,31)]

    from django import forms
    class LogViewerForm(forms.Form):
        start_month = forms.ChoiceField(label = "Month",
                initial = "%d" % datetime.datetime.now().month,
                choices = start_month_choices)
        start_day = forms.ChoiceField(label = "Day",
                initial = "%d" % datetime.datetime.now().day,
                choices = start_day_choices)
        only_lustre = forms.BooleanField(required = False,
                                         initial = True,
                                         label = "Only Lustre messages?")

    if request.method == 'GET' and 'start_month' in request.GET:
        # If the form has been submitted...
        form = LogViewerForm(request.GET) # A form bound to the POST data

        if form.is_valid(): # All validation rules pass
            display_month = int(form.cleaned_data['start_month'])
            display_day = int(form.cleaned_data['start_day'])
            only_lustre = form.cleaned_data['only_lustre']

            log_data = get_log_data(display_month, display_day, only_lustre)
        else:
            log_data = []

    else:
        form = LogViewerForm() # An unbound form
        log_data = get_log_data(0, 0, form.fields['only_lustre'].initial)

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
        host = forms.ModelChoiceField(queryset = ManagedHost.objects.all(), empty_label = "Any", required = False)
        severity = forms.ChoiceField((("", "Any"), (INFO, 'info'), (WARNING, 'warning'), (ERROR, 'error')), required = False)
        event_type = forms.ChoiceField(type_choices(), required = False)

    filter_args = []
    filter_kwargs = {}

    if request.method == 'GET' and not 'host' in request.GET:
        form = EventFilterForm()
    else:
        form = EventFilterForm(data = request.GET)
        if form.is_valid():
            if form.cleaned_data['host']:
                filter_kwargs['host'] = form.cleaned_data['host']
            if form.cleaned_data['severity']:
                filter_kwargs['severity'] = form.cleaned_data['severity']
            klass = form.cleaned_data['event_type']
            if klass:
                from django.db.models import Q
                klass_lower = klass.lower()
                filter_args.append(~Q(**{klass_lower: None}))

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

    if commit:
        from django.db.utils import IntegrityError
        try:
            ManagedHost.create_from_string(address)
        except IntegrityError,e:
            raise RuntimeError("Cannot add '%s', possible duplicate address. (%s)" % (address, e))

        result = {'success': True}
    else:
        # TODO: let user specify agent path
        host, ssh_monitor = SshMonitor.from_string(address)

        from tasks import test_host_contact
        job = test_host_contact.delay(host, ssh_monitor)
        result = {'task_id': job.task_id, 'success': True}

    return HttpResponse(json.dumps(result), mimetype = 'application/json')

