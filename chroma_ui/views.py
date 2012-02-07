
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.shortcuts import render_to_response
from django.template import RequestContext


# index
# if you got no local_settings.py goto setup
# if you got a db but no tables go to syncdb+create user
# else goto dashboard

LOCAL_SETTINGS_FILE = "local_settings.py"


def _unconfigured():
    """Return True if we cannot talk to a database"""
    import settings
    import os
    project_dir = os.path.dirname(os.path.realpath(settings.__file__))
    local_settings = os.path.join(project_dir, LOCAL_SETTINGS_FILE)
    return not os.path.exists(local_settings)


def _unpopulated():
    """Return True if we can talk to a database but
    our tables are absent or no Users exist"""
    from django.db.utils import DatabaseError
    try:
        from django.contrib.auth.models import User
        count = User.objects.count()
        if count == 0:
            return True
        else:
            return False
    except DatabaseError:
        # FIXME: SECURITY: if the attacker can somehow generate a
        # DatabaseError, they can get at the setup page.
        return True

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
import django.forms as forms
import django.contrib.auth


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
            #if database_form.cleaned_data['local']:
                # No extra configuration required, we ship with local
                # MySQL server enabled
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

            # TODO: Okay, now we have a database, we can invoke the equivalent of syncdb --migrate --noinput
            from django.core.management import ManagementUtility
            ManagementUtility(['', 'syncdb', '--noinput', '--migrate']).execute()

            # TODO: now that we have syncdb'd, start up the services and mark
            # them to start on boot

            user_form.save()
            # TODO: make the resulting user a superuser
            return HttpResponseRedirect(reverse('chroma_ui.views.dashboard'))

    elif request.method == "GET":
        user_form = InstallationUserForm()
        database_form = DatabaseForm()

    return render_to_response("installation.html",
            RequestContext(request, {
                'user_form': user_form,
                'database_form': database_form}))


def configure(request):
    return render_to_response("configuration_home.html",
            RequestContext(request, {}))


def filesystem_tab(request):
    return render_to_response("lustre_fs_configuration.html",
            RequestContext(request, {}))


def mgt_tab(request):
    return render_to_response("new_mgt.html",
            RequestContext(request, {}))


def volume_tab(request):
    return render_to_response("volume_configuration.html",
            RequestContext(request, {}))


def server_tab(request):
    return render_to_response("server_configuration.html",
            RequestContext(request, {}))


def storage_tab(request):
    return render_to_response("storage_configuration.html",
            RequestContext(request, {}))


def filesystem_create_tab(request):
    return render_to_response("create_lustre_fs.html",
            RequestContext(request, {}))


def filesystem_edit_tab(request):
    fs_id = request.GET.get("fs_id")
    from chroma_core.models import ManagedFilesystem
    fs = ManagedFilesystem.objects.get(pk = fs_id)
    return render_to_response("edit_fs.html",
            RequestContext(request, {"fs_name": fs.name, "fs_id": fs_id}))


def dashboard(request):
    return render_to_response("index.html",
            RequestContext(request, {}))


def dbalerts(request):
    return render_to_response("db_alerts.html",
            RequestContext(request, {}))


def dbevents(request):
    return render_to_response("db_events.html",
            RequestContext(request, {}))


def dblogs(request):
    return render_to_response("db_logs.html",
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
    import json
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
