
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# Create your views here.
from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.shortcuts import render_to_response
from django.template import RequestContext


def hydracm(request):
    return render_to_response("configuration_home.html",
            RequestContext(request, {}))

def hydracmfstab(request):
    return render_to_response("lustre_fs_configuration.html",
            RequestContext(request, {}))

def hydracmmgttab(request):
    return render_to_response("new_mgt.html",
            RequestContext(request, {}))

def hydracmvolumetab(request):
    return render_to_response("volume_configuration.html",
            RequestContext(request, {}))

def hydracmservertab(request):
    return render_to_response("server_configuration.html",
            RequestContext(request, {}))

def storage_tab(request):
    return render_to_response("storage_configuration.html",
            RequestContext(request, {}))

def hydracmnewfstab(request):
    return render_to_response("create_lustre_fs.html",
            RequestContext(request, {}))

def hydracmeditfs(request):
    fs_id=request.GET.get("fs_id")
    from configure.models import ManagedFilesystem
    fs = ManagedFilesystem.objects.get(pk = fs_id)
    return render_to_response("edit_fs.html",
            RequestContext(request, {"fs_name": fs.name, "fs_id":fs_id}))

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

    from configure.lib.state_manager import StateManager
    StateManager.set_state(stateful_object, new_state)

    return HttpResponse(status = 201)

def _jobs_json():
    import json
    from django.core.urlresolvers import reverse
    from datetime import timedelta, datetime
    from django.db.models import Q
    from configure.models import Job

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

    from configure.lib.state_manager import StateManager
    state_manager = StateManager()

    from configure.models import ManagedOst, ManagedMdt, ManagedMgs, ManagedHost, ManagedTargetMount, ManagedFilesystem, LNetConfiguration, StatefulObject

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
                        "url": reverse('hydracm.views.set_state', kwargs={
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
    from configure.models import Job
    job = get_object_or_404(Job, id = job_id)
    job = job.downcast()

    return render_to_response("job.html", RequestContext(request, {
        'job': job 
        })) 


def jobs_json(request):
    return HttpResponse(_jobs_json(), 'application/json')




