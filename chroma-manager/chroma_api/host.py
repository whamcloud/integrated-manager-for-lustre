#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
from chroma_core.services.job_scheduler import job_scheduler_client
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


class HostTestValidation(HostValidation):

    def is_valid(self, bundle, request=None):
        errors = super(HostTestValidation, self).is_valid(bundle, request)

        try:
            auth_type = bundle.data['auth_type']
            if auth_type == 'root_password_choice':
                try:
                    root_password = bundle.data.get('root_password')
                except KeyError:
                    errors['root_password'].append("This field is mandatory")
                else:
                    if not len(root_password.strip()):
                        errors['root_password'].append("This field is mandatory")
            elif auth_type == 'private_key_choice':
                try:
                    private_key = bundle.data.get('private_key')
                except KeyError:
                    errors['private_key'].append("This field is mandatory")
                else:
                    if not len(private_key.strip()):
                        errors['private_key'].append("This field is mandatory")
        except KeyError:
            #  What?  Now auth_type? assume existing key default case.
            pass

        return errors


def _host_params(bundle):
#  See the UI (e.g. server_configuration.js)
    return {'address': bundle.data.get('address'),
            'root_pw': bundle.data.get('root_password'),
            'pkey': bundle.data.get('private_key'),
            'pkey_pw': bundle.data.get('private_key_passphrase')}


class HostResource(MetricResource, StatefulModelResource):
    """
    Represents a Lustre server that is being monitored and managed from the Command Center.

    PUTs to this resource must have the ``state`` attribute set.

    POSTs to this resource must have the ``address`` attribute set.
    """
    nids = fields.ListField(null = True)
    root_pw = fields.CharField(help_text = "ssh root password to new server.")
    private_key = fields.CharField(help_text = "ssh private key matching a "
                                               "public key on the new server.")
    private_key_passphrase = fields.CharField(help_text = "passphrase to "
                                                          "decrypt private key")

    def dehydrate_nids(self, bundle):
        return [n.nid_string for n in Nid.objects.filter(
            lnet_configuration = bundle.obj.lnetconfiguration)]

    class Meta:
        queryset = ManagedHost.objects.select_related(
            'lnetconfiguration').prefetch_related('lnetconfiguration__nid_set')
        resource_name = 'host'
        excludes = ['not_deleted']
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
            host_params = _host_params(bundle)
            host, command = job_scheduler_client.JobSchedulerClient.create_host_ssh(
                **host_params)
        except RpcError, e:
            # Rather stretching the meaning of "BAD REQUEST", say that this
            # request is bad on the basis that the user specified a host that
            # is (for some reason) not playing ball.
            args = {'address': ["Cannot add host at this address: %s" % e]}
            raise custom_response(self, request, http.HttpBadRequest, args)
        else:
            args = {'command': dehydrate_command(command),
                    'host': self.full_dehydrate(
                        self.build_bundle(obj = host)).data}
            raise custom_response(self, request, http.HttpAccepted, args)

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
    used prior to creating the host.  Only supports POST with the 'address'
    field.

    """
    address = fields.CharField(help_text = "Same as ``address`` "
                                           "field on host resource.")

    root_pw = fields.CharField(help_text = "ssh root password to new server.")
    private_key = fields.CharField(help_text = "ssh private key matching a "
                                               "public key on the new server.")
    private_key_passphrase = fields.CharField(help_text = "passphrase to "
                                                          "decrypt private key")

    auth_type = fields.CharField(help_text = "SSH authentication type. "
         "If has the value 'root_password_choice', then the root_password "
         "field must be non-empty, and if the value is 'private_key_choice' "
         "then the private_key field must be non empty.  All other values are "
         "ignored and assume existing private key.  This field is not for "
         "actual ssh connections.  It is used to validate that enough "
         "information is available to attempt the chosen auth_type.")

    class Meta:
        list_allowed_methods = ['post']
        detail_allowed_methods = []
        resource_name = 'test_host'
        authentication = AnonymousAuthentication()
        authorization = PermissionAuthorization('add_managedhost')
        object_class = dict
        validation = HostTestValidation()

    def obj_create(self, bundle, request = None, **kwargs):

        result = job_scheduler_client.JobSchedulerClient.test_host_contact(
            **_host_params(bundle))

        raise custom_response(self, request, http.HttpAccepted, result)
