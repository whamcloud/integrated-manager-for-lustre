#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from collections import defaultdict
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services.rpc import RpcError, RpcTimeout
from chroma_core.services import log_register
from tastypie.validation import Validation

from chroma_core.models import ManagedHost, Nid, ManagedFilesystem, ServerProfile, LustreClientMount

from django.shortcuts import get_object_or_404
from django.db.models import Q

import tastypie.http as http
from tastypie.resources import Resource, ModelResource
from tastypie import fields
from chroma_api.utils import custom_response, StatefulModelResource, MetricResource, dehydrate_command
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.authentication import PermissionAuthorization

log = log_register(__name__)


class HostValidation(Validation):
    mandatory_message = "This field is mandatory"

    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)
        if request.method != 'POST':
            return errors

        try:
            bundle.data['server_profile']
        except KeyError:
            errors['server_profile'].append(self.mandatory_message)

        try:
            address = bundle.data['address']
        except KeyError:
            errors['address'].append(self.mandatory_message)
        else:
            # TODO: validate URI

            host_must_exist = bundle.data.get("host_must_exist", None)

            if (host_must_exist != None) and (host_must_exist != ManagedHost.objects.filter(address=address).exists()):
                errors['address'].append("Host %s is %s in use by IML" % (address, "not" if host_must_exist else "already"))

        return errors


class HostTestValidation(HostValidation):

    def is_valid(self, bundle, request=None):
        errors = super(HostTestValidation, self).is_valid(bundle, request)

        try:
            auth_type = bundle.data['auth_type']
            if auth_type == 'id_password_root':
                try:
                    root_password = bundle.data['root_password']
                except KeyError:
                    errors['root_password'].append(self.mandatory_message)
                else:
                    if not len(root_password.strip()):
                        errors['root_password'].append(self.mandatory_message)
            elif auth_type == 'private_key_choice':
                try:
                    private_key = bundle.data['private_key']
                except KeyError:
                    errors['private_key'].append(self.mandatory_message)
                else:
                    if not len(private_key.strip()):
                        errors['private_key'].append(self.mandatory_message)
        except KeyError:
            #  What?  Now auth_type? assume existing key default case.
            pass

        return errors


def _host_params(bundle, address = None):
#  See the UI (e.g. server_configuration.js)
    return {'address': bundle.data.get('address', address),
            'root_pw': bundle.data.get('root_password'),
            'pkey': bundle.data.get('private_key'),
            'pkey_pw': bundle.data.get('private_key_passphrase')}


class ServerProfileResource(ModelResource):
    class Meta:
        queryset = ServerProfile.objects.all()
        resource_name = 'server_profile'
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        ordering = ['managed', 'default']
        list_allowed_methods = ['get']
        readonly = ['ui_name']
        filtering = {'name': ['exact'], 'managed': ['exact'],
                     'worker': ['exact'], 'default': ['exact']}


class ClientMountResource(ModelResource):
    # This resource is only used for integration testing.

    host = fields.ToOneField('chroma_api.host.HostResource', 'host')
    filesystem = fields.ToOneField('chroma_api.filesystem.FilesystemResource', 'filesystem')
    mountpoint = fields.CharField()

    class Meta:
        queryset = LustreClientMount.objects.all()
        resource_name = 'client_mount'
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        list_allowed_methods = ['get', 'post']
        filtering = {'host': ['exact'], 'filesystem': ['exact']}

    def prepare_mount(self, client_mount):
        return self.alter_detail_data_to_serialize(None, self.full_dehydrate(
               self.build_bundle(obj = client_mount))).data

    def obj_create(self, bundle, request = None, **kwargs):
        host = self.fields['host'].hydrate(bundle).obj
        filesystem = self.fields['filesystem'].hydrate(bundle).obj
        mountpoint = bundle.data['mountpoint']

        client_mount = JobSchedulerClient.create_client_mount(host, filesystem,
                                                              mountpoint)

        args = dict(client_mount = self.prepare_mount(client_mount))
        raise custom_response(self, request, http.HttpAccepted, args)


class HostResource(MetricResource, StatefulModelResource):
    """
    Represents a Lustre server that is being monitored and managed from the manager server.

    PUTs to this resource must have the ``state`` attribute set.

    POSTs to this resource must have the ``address`` attribute set.
    """
    nids = fields.ListField(null = True)
    member_of_active_filesystem = fields.BooleanField()
    client_mounts = fields.ListField(null = True)
    root_pw = fields.CharField(help_text = "ssh root password to new server.")
    private_key = fields.CharField(help_text = "ssh private key matching a "
                                               "public key on the new server.")
    private_key_passphrase = fields.CharField(help_text = "passphrase to "
                                                          "decrypt private key")

    server_profile = fields.ToOneField(ServerProfileResource, 'server_profile',
                                       full = True)

    def dehydrate_nids(self, bundle):
        return [n.nid_string for n in Nid.objects.filter(
            lnet_configuration = bundle.obj.lnetconfiguration)]

    def dehydrate_member_of_active_filesystem(self, bundle):
        return bundle.obj.member_of_active_filesystem

    def dehydrate_client_mounts(self, bundle):
        from chroma_core.lib.cache import ObjectCache
        from chroma_core.models import LustreClientMount
        search = lambda cm: cm.host == bundle.obj
        mounts = ObjectCache.get(LustreClientMount, search)
        return [{'filesystem_name': mount.filesystem.name,
                 'mountpoint': mount.mountpoint,
                 'state': mount.state} for mount in mounts]

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
        readonly = ['nodename', 'fqdn', 'nids', 'member_of_active_filesystem',
                    'needs_fence_reconfiguration', 'needs_update', 'boot_time',
                    'corosync_reported_up', 'client_mounts']
        # HYD-2256: remove these fields when other auth schemes work
        readonly += ['root_pw', 'private_key_passphrase', 'private_key']
        validation = HostValidation()
        always_return_data = True

        filtering = {'id': ['exact'],
                     'fqdn': ['exact', 'startswith'],
                     'role': ['exact']}

    def obj_update(self, bundle, request, **kwargs):
        # If the host that is being updated is in the undeployed state then this is a special case and the normal
        # state change doesn't work because we need to provide some parameters to the allow the ssh connection to
        # bootstrap the agent into existance.
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))

        assert isinstance(bundle.obj, ManagedHost)

        if bundle.obj.state == 'undeployed':
            self._create_host(bundle.obj.address, bundle, request)

        return super(HostResource, self).obj_update(bundle, request, **kwargs)

    def obj_create(self, bundle, request = None, **kwargs):
        # FIXME HYD-1657: we get errors back just fine when something goes wrong
        # during registration, but the UI tries to format backtraces into
        # a 'validation errors' dialog which is pretty ugly.

        if bundle.data.get('failed_validations'):
            log.warning("Attempting to create host %s after failed validations: %s" % (bundle.data.get('address'), bundle.data.get('failed_validations')))

        self._create_host(None, bundle, request)

    def _create_host(self, address, bundle, request):
        # Resolve a server profile URI to a record
        profile = self.fields['server_profile'].hydrate(bundle).obj

        try:
            host, command = JobSchedulerClient.create_host_ssh(server_profile=profile.name,
                                                               **_host_params(bundle, address))
        except RpcError, e:
            # Return 400, a failure here could mean the address was already occupied, or that
            # we couldn't reach that address using SSH (network or auth problem)
            raise custom_response(self, request, http.HttpBadRequest,
                {'address': ["Cannot add host at this address: %s" % e],
                'traceback': e.traceback})
        else:
            #  TODO:  Could simplify this by adding a 'command' key to the
            #  bundle, then optionally handling dehydrating that
            #  in super.alter_detail_data_to_serialize.  That way could
            #  return from this method avoiding all this extra code, and
            #  providing a central handling for all things that migth have
            #  a command argument.  NB:  not tested, and not part of any ticket
            args = {'command': dehydrate_command(command),
                    'host': self.alter_detail_data_to_serialize(None,
                                self.full_dehydrate(
                                    self.build_bundle(obj = host))).data
            }
            raise custom_response(self, request, http.HttpAccepted, args)

    def apply_filters(self, request, filters = None):
        objects = super(HostResource, self).apply_filters(request, filters)
        try:
            fs = get_object_or_404(ManagedFilesystem, pk = request.GET['filesystem_id'])
            objects = objects.filter((Q(managedtargetmount__target__managedmdt__filesystem = fs) | Q(managedtargetmount__target__managedost__filesystem = fs)) | Q(managedtargetmount__target__id = fs.mgs.id))
        except KeyError:
            # Not filtering on filesystem_id
            pass

        # convenience filter for the UI client
        if request.GET.get('worker', False):
            objects = objects.filter(server_profile__worker = True)

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

    server_profile = fields.CharField(help_text="Server profile chosen")

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
        authorization = PermissionAuthorization('chroma_core.add_managedhost')
        object_class = dict
        validation = HostTestValidation()

    def obj_create(self, bundle, request = None, **kwargs):

        try:
            result = JobSchedulerClient.test_host_contact(**_host_params(bundle))
        except RpcTimeout:
            raise custom_response(self, request, http.HttpBadRequest, {'address': ["Cannot contact host at this address:"]})

        raise custom_response(self, request, http.HttpAccepted, result)
