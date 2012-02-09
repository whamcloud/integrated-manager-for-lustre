#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import ManagedHost
from django.db import IntegrityError

import tastypie.http as http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import Resource
from tastypie import fields
from chroma_api.utils import custom_response, StatefulModelResource

from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.authentication import PermissionAuthorization


class HostResource(StatefulModelResource):
    class Meta:
        queryset = ManagedHost.objects.all()
        resource_name = 'host'
        excludes = ['not_deleted']
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()

        # So that we can return Commands for PUTs
        always_return_data = True

        filtering = {'id': ['exact'],
                     'fqdn': ['exact']}

    def obj_create(self, bundle, request = None, **kwargs):
        # FIXME: we implement this instead of letting it go
        # straight through to the model because the model
        # does some funny stuff in create_from_string.  Really
        # ManagedHost should be refactored so that a simple save()
        # does the job
        try:
            bundle.obj = ManagedHost.create_from_string(bundle.data['host_name'])
        except IntegrityError:
            raise ImmediateHttpResponse(response = http.HttpBadRequest)
        return bundle


class HostTestResource(Resource):
    hostname = fields.CharField()

    class Meta:
        list_allowed_methods = ['post']
        detail_allowed_methods = []
        resource_name = 'test_host'
        authentication = AnonymousAuthentication()
        authorization = PermissionAuthorization('add_managedhost')
        object_class = dict

    def obj_create(self, bundle, request = None, **kwargs):
        from chroma_core.tasks import test_host_contact
        from chroma_core.models import Monitor
        host = ManagedHost(address = bundle.data['hostname'])
        host.monitor = Monitor(host = host)
        task = test_host_contact.delay(host)
        raise custom_response(self, request, http.HttpAccepted, {'task_id': task.task_id, 'status': task.status})
