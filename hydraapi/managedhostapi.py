#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
#REST API Controller for Lustre File systems resource in configure namespace
from django.core.management import setup_environ
from django.shortcuts import get_object_or_404
# Hydra server imports
import settings
setup_environ(settings)

from configure.models import (ManagedHost, ManagedFilesystem)
from configure.lib.state_manager import StateManager
from requesthandler import (AnonymousRESTRequestHandler, extract_request_args)
from hydraapi.requesthandler import APIResponse


class ManagedHostsHandler (AnonymousRESTRequestHandler):
    @extract_request_args('host_id=None', 'filesystem_id=None')
    def get(self, request, host_id = None, filesystem_id = None):
        hosts = []
        if host_id:
            host = get_object_or_404(ManagedHost, pk = host_id)
            hosts.append(host)
        elif filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            hosts = fs.get_servers()
        else:
            hosts = ManagedHost.objects.all()
        hosts_info = []
        for h in hosts:
            _host = h.to_dict()
            _host['available_transitions'] = StateManager.available_transitions(h)
            hosts_info.append(_host)
        return hosts_info

    @extract_request_args('host_name')
    def post(self, request, host_name):
        host = ManagedHost.create_from_string(host_name)
        result = {'id': host.id, 'host': host.address}
        api_res = APIResponse(result, 201)
        return api_res

    @extract_request_args('id', 'state')
    def put(self, request, id, state):
        host = get_object_or_404(ManagedHost, pk = id)
        if state not in host.states:
            raise Exception('Invalid state, possible states for this host are:%' % host.states)
        transition_job = StateManager.set_state(host, state)
        return {'id': host.id, 'job_id': transition_job.task_id, 'status': transition_job.status}

    @extract_request_args('id')
    def remove(self, request, id):
        host = get_object_or_404(ManagedHost, pk = id)
        transition_job = StateManager.set_state(host, 'removed')
        return {'id': host.id, 'job_id': transition_job.task_id, 'status': transition_job.status}
