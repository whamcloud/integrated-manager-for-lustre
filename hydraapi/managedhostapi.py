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
from requesthandler import AnonymousRESTRequestHandler
from hydraapi.requesthandler import APIResponse


class ManagedHostsHandler (AnonymousRESTRequestHandler):
    def get(self, request, id = None, filesystem_id = None):

        def host_dict_with_transitions(host):
            _host = host.to_dict()
            _host['available_transitions'] = StateManager.available_transitions(host)
            return _host

        hosts = []
        if id:
            host = get_object_or_404(ManagedHost, pk = id)
            return host_dict_with_transitions(host)
        elif filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            hosts = fs.get_servers()
        else:
            hosts = ManagedHost.objects.all()

        return [host_dict_with_transitions(h) for h in hosts]

    def post(self, request, host_name):
        host = ManagedHost.create_from_string(host_name)
        return APIResponse(host.to_dict(), 201)

        result = {'id': host.id, 'host': host.address}
        api_res = APIResponse(result, 201)
        return api_res

    def delete(self, request, id):
        # NB This is equivalent to a call to /api/transition with matching content-type/id/state
        from configure.models import Command
        host = get_object_or_404(ManagedHost, pk = id)
        command = Command.set_state(host, 'removed')
        return APIResponse(command.to_dict(), 202)


class TestHost(AnonymousRESTRequestHandler):
    def get(self, request, hostname):
        from monitor.tasks import test_host_contact
        from configure.models import Monitor
        host = ManagedHost(address = hostname)
        host.monitor = Monitor(host = host)
        job = test_host_contact.delay(host)
        return {'task_id': job.task_id, 'status': job.status}
