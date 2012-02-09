
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json

from django.shortcuts import render_to_response
from django.template import RequestContext

import settings

# index
# if you got no local_settings.py goto setup
# if you got a db but no tables go to syncdb+create user
# else goto dashboard


def _unconfigured():
    """Return True if we cannot talk to a database"""
    import os
    project_dir = os.path.dirname(os.path.realpath(settings.__file__))
    local_settings = os.path.join(project_dir, settings.LOCAL_SETTINGS_FILE)
    return not os.path.exists(local_settings)


def _unpopulated():
    """Return True if we can talk to a database but
    our tables are absent"""
    from django.db.utils import DatabaseError
    try:
        from chroma_core.models.host import ManagedHost
        ManagedHost.objects.count()
    except DatabaseError:
        return True

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
import django.forms as forms
import django.contrib.auth
import hashlib


class DatabaseForm(forms.Form):
    local = forms.BooleanField(label = "Use local MySQL server", required = False, initial = True)
    address = forms.RegexField(label = "Address", required = False,
            regex = "^(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|\b-){0,61}[0-9A-Za-z])?(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|\b-){0,61}[0-9A-Za-z])?)*\.?$",
            help_text = "MySQL server address (hostname or IP address)")
    port = forms.IntegerField(required = False)
    db_username = forms.CharField(label = "Username", required = False, max_length = 16)
    db_password = forms.CharField(label = "Password", required = False, widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super(DatabaseForm, self).clean()
        local = cleaned_data.get('local')
        if local:
            if cleaned_data['address'] or cleaned_data['port'] or cleaned_data['db_username'] or cleaned_data['db_password']:
                raise forms.ValidationError("Cannot specify access information for local server")
        else:
            if not 'address' in cleaned_data:
                raise forms.ValidationError("Address must be supplied for remote server")
            if not 'username' in cleaned_data:
                raise forms.ValidationError("Username must be supplied for remote server")
        return cleaned_data


class InstallationUserForm(django.contrib.auth.forms.UserCreationForm):
    """A variant of UserCreationForm that skips uniqueness checks to
    avoid touching the database (which might not exist yet)"""
    def clean_username(self):
        return self.cleaned_data["username"]

    def validate_unique(self):
        pass


def index(request):
    """Redirect to /setup/ on a new system, or /dashboard/
    on a system that has already been set up"""
    if _unconfigured():
        return HttpResponseRedirect(reverse('chroma_ui.views.installation'))
    else:
        return HttpResponseRedirect(reverse('chroma_ui.views.dashboard'))


def _httpd_pid():
    try:
        pid_str = open("/var/run/httpd/httpd.pid").read()
        m = hashlib.md5()
        m.update(pid_str)
        return m.hexdigest()
    except IOError, e:
        print "IOError %s" % e
        return 0


def installation_status(request):
    httpd_pid = _httpd_pid()
    if 'httpd_pid' in request.GET:
        if httpd_pid != request.GET['httpd_pid']:
            restarted = True
        else:
            restarted = False
    else:
        restarted = None

    result = {
            "populated": not _unpopulated(),
            "restarted": restarted
            }

    return HttpResponse(json.dumps(result), mimetype = "application/json")


def installation(request):
    if not _unconfigured():
        return HttpResponseForbidden()

    if request.method == "POST":
        user_form = InstallationUserForm(request.POST)
        #database_form = DatabaseForm(request.POST)
        #user_form_valid = user_form.is_valid()
        #database_form_valid = database_form.is_valid()
        #if user_form_valid and database_form_valid:
        if user_form.is_valid():
            databases = settings.DATABASES
            #if database_form.cleaned_data['local']:
                # No extra configuration required, we ship with local
                # MySQL server enabled
                #databases = settings.DATABASES
            #    pass
            #else:
                #TODO
                # Try contacting the remote server
                # Generate a local_settings.py file for the server
                # Set CELERY_RESULT_DBURI
                # Monkey patch existing settings.DATABASES
                # Then we can write out users and settings
                # And finally we should get apache to restart, so that
                # things like CELERY_RESULT_DBURI are picked up
           #     raise NotImplementedError("Remote server configuration not implemented")

            # Get an unsaved User object
            user = super(django.contrib.auth.forms.UserCreationForm, user_form).save(commit = False)
            user.is_superuser = True

            # Perform post-syncdb setup of services (requires root, so have
            # to go out to external script to make it happen)
            from chroma_core.tasks import installation
            pid = _httpd_pid()
            installation.delay(databases, user)

            # That delayed task is going to restart apache (and the service worker)
            # so we're going to return the user a waiting polling page.
            return render_to_response("installation_wait.html", RequestContext(request, {
                'httpd_pid': pid
            }))

    elif request.method == "GET":
        user_form = InstallationUserForm()
        database_form = DatabaseForm()

    return render_to_response("installation.html",
            RequestContext(request, {
                'user_form': user_form,
                'database_form': database_form}))


def configure(request):
    return render_to_response("configuration.html",
            RequestContext(request, {}))


def filesystem_tab(request):
    return render_to_response("filesystem_list.html",
            RequestContext(request, {}))


def mgt_tab(request):
    return render_to_response("mgt_tab.html",
            RequestContext(request, {}))


def volume_tab(request):
    return render_to_response("volume_tab.html",
            RequestContext(request, {}))


def server_tab(request):
    return render_to_response("server_tab.html",
            RequestContext(request, {}))


def storage_tab(request):
    return render_to_response("storage_tab.html",
            RequestContext(request, {}))


def filesystem_create_tab(request):
    return render_to_response("filesystem_create.html",
            RequestContext(request, {}))


def filesystem_edit_tab(request):
    return render_to_response("filesystem_detail.html",
            RequestContext(request, {}))


def dashboard(request):
    return render_to_response("dashboard.html",
            RequestContext(request, {}))


def dbalerts(request):
    return render_to_response("alerts.html",
            RequestContext(request, {}))


def dbevents(request):
    return render_to_response("events.html",
            RequestContext(request, {}))


def dblogs(request):
    return render_to_response("logs.html",
            RequestContext(request, {}))


def states(request):
    return render_to_response("states.html", RequestContext(request, {
        'initial_data': _jobs_json()
        }))


from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404


def set_state(request, content_type_id, stateful_object_id, new_state):
    stateful_object_klass = ContentType.objects.get(id = content_type_id).model_class()
    stateful_object = stateful_object_klass.objects.get(id = stateful_object_id)

    from chroma_core.lib.state_manager import StateManager
    StateManager.set_state(stateful_object, new_state)

    return HttpResponse(status = 201)


def _jobs_json():
    from django.core.urlresolvers import reverse
    from datetime import timedelta, datetime
    from django.db.models import Q
    from chroma_core.models import Job

    jobs = Job.objects.filter(~Q(state = 'complete') | Q(created_at__gte=datetime.now() - timedelta(minutes=60)))
    jobs_dicts = []
    for job in jobs:
        jobs_dicts.append({
            'id': job.id,
            'state': job.state,
            'errored': job.errored,
            'cancelled': job.cancelled,
            'created_at': "%s" % job.created_at,
            'description': job.description()
        })

    from chroma_core.lib.state_manager import StateManager
    state_manager = StateManager()

    from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedHost, ManagedTargetMount, ManagedFilesystem, LNetConfiguration, StatefulObject

    from itertools import chain
    stateful_objects = []
    klasses = [ManagedOst, ManagedMdt, ManagedMgs, ManagedHost, ManagedTargetMount, ManagedFilesystem, LNetConfiguration]
    for i in chain(*[k.objects.all() for k in klasses]):
        actions = []
        if isinstance(i, StatefulObject):
            state = i.state
            transitions = state_manager.available_transitions(i)
            if transitions == None:
                busy = True
            else:
                busy = False
                for transition in transitions:
                    actions.append({
                        "name": transition['state'],
                        "caption": transition['verb'],
                        "url": reverse('chroma_ui.views.set_state', kwargs={
                            "content_type_id": "%s" % ContentType.objects.get_for_model(i).id,
                            "stateful_object_id": "%s" % i.id,
                            "new_state": transition['state']
                            }),
                        "ajax": True
                        })
        else:
            state = ""

        stateful_objects.append({
            "id": i.id,
            "__str__": "%s" % i,
            "state": state,
            "actions": actions,
            "content_type_id": ContentType.objects.get_for_model(i).id,
            "busy": busy
            })

    return json.dumps({
                'jobs': jobs_dicts,
                'stateful_objects': stateful_objects
            }, indent = 4)


def job(request, job_id):
    from chroma_core.models import Job
    job = get_object_or_404(Job, id = job_id)
    job = job.downcast()

    return render_to_response("job.html", RequestContext(request, {
        'job': job
        }))


def jobs_json(request):
    return HttpResponse(_jobs_json(), 'application/json')
