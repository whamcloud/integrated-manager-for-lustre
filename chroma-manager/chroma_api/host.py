#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
from tastypie.validation import Validation

from chroma_core.models import ManagedHost

import tastypie.http as http
from tastypie.resources import Resource
from tastypie import fields
from chroma_api.utils import custom_response, StatefulModelResource, MetricResource, dehydrate_command
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.authentication import PermissionAuthorization


class HostValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)
        if request.method != 'POST':
            return errors

        try:
            address = bundle.data['address']
        except KeyError:
            errors['address'].append("This field is mandatory")
        else:
            if not len(address.strip()):
                errors['address'].append("This field is mandatory")
            else:
                # TODO: validate URI
                try:
                    ManagedHost.objects.get(address = address)
                    errors['address'].append("This address is already in use")
                except ManagedHost.DoesNotExist:
                    pass

        return errors


class HostResource(MetricResource, StatefulModelResource):
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
        validation = HostValidation()
        always_return_data = True

        filtering = {'id': ['exact'],
                     'fqdn': ['exact']}

    def obj_create(self, bundle, request = None, **kwargs):
        host, command = ManagedHost.create_from_string(bundle.data['address'])
        raise custom_response(self, request, http.HttpAccepted,
                {'command': dehydrate_command(command),
                 'host': self.full_dehydrate(self.build_bundle(obj = host)).data})


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
        validation = HostValidation()

    def obj_create(self, bundle, request = None, **kwargs):
        from chroma_core.models.utils import await_async_result
        from chroma_core.tasks import test_host_contact

        host = ManagedHost(address = bundle.data['address'])
        async_result = test_host_contact.delay(host)
        result = await_async_result(async_result)

        raise custom_response(self, request, http.HttpAccepted, result)
