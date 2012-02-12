
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json

from django.shortcuts import render_to_response
from django.template import RequestContext

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse


def index(request):
    """Redirect to /installation/ on a new system, or /dashboard/
    on a system that has already been set up"""

    from chroma_core.lib.service_config import ServiceConfig
    if not ServiceConfig().configured():
        return HttpResponseRedirect(reverse('chroma_ui.views.installation'))
    else:
        return HttpResponseRedirect(reverse('chroma_ui.views.dashboard'))


def installation(request):
    return render_to_response("installation.html",
            RequestContext(request, {}))


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


def user_tab(request):
    return render_to_response("user_tab.html",
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
