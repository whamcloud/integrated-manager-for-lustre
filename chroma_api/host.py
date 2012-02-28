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
from chroma_api.utils import custom_response, StatefulModelResource, dehydrate_command

from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.authentication import PermissionAuthorization

from chroma_api import api_log


class HostResource(StatefulModelResource):
    """
    Represents a Lustre server which Chroma server is monitoring or managing.  When PUTing, requires the ``state`` field.  When POSTing, requires the ``address`` field.
    """
    class Meta:
        queryset = ManagedHost.objects.all()
        resource_name = 'host'
        excludes = ['not_deleted', 'agent_token']
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        ordering = ['fqdn']
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'put', 'delete']
        readonly = ['nodename', 'fqdn']

        # So that we can return Commands for PUTs
        always_return_data = True

        filtering = {'id': ['exact'],
                     'fqdn': ['exact']}

    def obj_create(self, bundle, request = None, **kwargs):
        try:
            host, command = ManagedHost.create_from_string(bundle.data['address'])
            raise custom_response(self, request, http.HttpAccepted,
                    {'command': dehydrate_command(command),
                     'host': self.full_dehydrate(self.build_bundle(obj = host)).data})
        except IntegrityError, e:
            api_log.error(e)
            raise ImmediateHttpResponse(response = http.HttpBadRequest({'address': "%s" % e}))


class HostTestResource(Resource):
    """
    A request to test a potential host address for accessibility, typically
    used prior to creating the host.  Only supports POST with the 'address' field.
    """
    address = fields.CharField(help_text = "Same as ``address`` field on host resource.")

    class Meta:
        list_allowed_methods = ['post']
        detail_allowed_methods = []
        resource_name = 'test_host'
        authentication = AnonymousAuthentication()
        authorization = PermissionAuthorization('add_managedhost')
        object_class = dict

    def obj_create(self, bundle, request = None, **kwargs):
        from chroma_core.tasks import test_host_contact
        host = ManagedHost(address = bundle.data['address'])
        task = test_host_contact.delay(host)
        raise custom_response(self, request, http.HttpAccepted, {'task_id': task.task_id, 'status': task.status})
