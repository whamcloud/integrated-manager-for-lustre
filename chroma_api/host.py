#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import (ManagedHost, ManagedFilesystem)
from chroma_core.lib.state_manager import StateManager
from requesthandler import AnonymousRESTRequestHandler
from chroma_api.requesthandler import APIResponse

from django.shortcuts import get_object_or_404


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
        from django.db import IntegrityError
        try:
            host = ManagedHost.create_from_string(host_name)
            return APIResponse(host.to_dict(), 201)
        except IntegrityError:
            return APIResponse("Host with address '%s' already exists" % host_name, 400)

    def remove(self, request, id):
        # NB This is equivalent to a call to /api/transition with matching content-type/id/state
        from chroma_core.models import Command
        host = get_object_or_404(ManagedHost, pk = id)
        command = Command.set_state(host, 'removed')
        return APIResponse(command.to_dict(), 202)


class TestHost(AnonymousRESTRequestHandler):
    def get(self, request, hostname):
        from monitor.tasks import test_host_contact
        from chroma_core.models import Monitor
        host = ManagedHost(address = hostname)
        host.monitor = Monitor(host = host)
        job = test_host_contact.delay(host)
        return {'task_id': job.task_id, 'status': job.status}
