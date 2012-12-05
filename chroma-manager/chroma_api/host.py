#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services.rpc import RpcError
from tastypie.validation import Validation

from chroma_core.models import ManagedHost, Nid, ManagedFilesystem

from django.shortcuts import get_object_or_404
from django.db.models import Q

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
    nids = fields.ListField(null = True)

    def dehydrate_nids(self, bundle):
        return [n.nid_string for n in Nid.objects.filter(lnet_configuration = bundle.obj.lnetconfiguration)]

    class Meta:
        queryset = ManagedHost.objects.all()
        resource_name = 'host'
        excludes = ['not_deleted', 'ssl_fingerprint']
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        ordering = ['fqdn']
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'put', 'delete']
        readonly = ['nodename', 'fqdn', 'nids', 'last_contact']
        validation = HostValidation()
        always_return_data = True

        filtering = {'id': ['exact'],
                     'fqdn': ['exact', 'startswith'],
                    'role': ['exact']}

    def obj_create(self, bundle, request = None, **kwargs):

        # FIXME: we get errors back just fine when something goes wrong
        # during registration, but the UI tries to format backtraces into
        # a 'validation errors' dialog which is pretty ugly.

        try:
            host, command = JobSchedulerClient.create_host_ssh(bundle.data['address'])
        except RpcError, e:
            # Rather stretching the meaning of "BAD REQUEST", say that this
            # request is bad on the basis that the user specified a host that
            # is (for some reason) not playing ball.
            raise custom_response(self, request, http.HttpBadRequest,
                {'address': ["Cannot add host at this address: %s" % e]})
        else:
            raise custom_response(self, request, http.HttpAccepted,
                {'command': dehydrate_command(command),
                 'host': self.full_dehydrate(self.build_bundle(obj = host)).data})

    def apply_filters(self, request, filters = None):
        objects = super(HostResource, self).apply_filters(request, filters)
        try:
            fs = get_object_or_404(ManagedFilesystem, pk = request.GET['filesystem_id'])
            objects = objects.filter((Q(managedtargetmount__target__managedmdt__filesystem = fs) | Q(managedtargetmount__target__managedost__filesystem = fs)) | Q(managedtargetmount__target__id = fs.mgs.id))
        except KeyError:
            # Not filtering on filesystem_id
            pass

        try:
            from chroma_api.target import KIND_TO_MODEL_NAME
            server_role = request.GET['role'].upper()
        except KeyError:
            # No 'role' argument
            pass
        else:
            target_model = KIND_TO_MODEL_NAME["%sT" % server_role[:-1]]
            objects = objects.filter(
                Q(managedtargetmount__target__content_type__model = target_model)
                &
                Q(managedtargetmount__target__not_deleted = True)
            )

        return objects.distinct()


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
        result = JobSchedulerClient.test_host_contact(bundle.data['address'])

        raise custom_response(self, request, http.HttpAccepted, result)
