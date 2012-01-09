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
    @extract_request_args('host_id=', 'filesystem_id=')
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

    # Note: For Managed Host Remove/Delete and State transitions, we are using common
    #       APIs. /api/transition/ and /api/transition_consequences/


class TestHost(AnonymousRESTRequestHandler):
    @extract_request_args('hostname')
    def get(self, request, hostname):
        from monitor.tasks import test_host_contact
        from configure.models import Monitor
        host = ManagedHost(address = hostname)
        host.monitor = Monitor(host = host)
        job = test_host_contact.delay(host)
        return {'task_id': job.task_id, 'status': job.status}
