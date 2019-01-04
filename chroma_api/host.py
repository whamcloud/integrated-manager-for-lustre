# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import re
from collections import defaultdict
from collections import namedtuple
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services import log_register
from tastypie.validation import Validation
from tastypie.utils import dict_strip_unicode_keys
from chroma_api.validation_utils import validate

import json


from chroma_core.models import ManagedHost, Nid, ManagedFilesystem, ServerProfile, LustreClientMount, Command
from chroma_core.models import LNetConfiguration, NetworkInterface
from long_polling_api import LongPollingAPI

from django.shortcuts import get_object_or_404
from django.db.models import Q
from tastypie.bundle import Bundle
from tastypie.exceptions import ImmediateHttpResponse


import tastypie.http as http
from tastypie.resources import Resource
from tastypie import fields
from chroma_api.utils import (
    custom_response,
    StatefulModelResource,
    MetricResource,
    dehydrate_command,
    BulkResourceOperation,
)
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.authentication import PermissionAuthorization
from iml_common.lib.evaluator import safe_eval
from chroma_api.utils import filter_fields_to_type
from chroma_api.chroma_model_resource import ChromaModelResource

log = log_register(__name__)


class HostValidation(Validation):
    mandatory_message = "This field is mandatory"

    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)
        if request.method != "POST":
            return errors
        for data in bundle.data.get("objects", [bundle.data]):
            if ("host" in data) and ("address" in data):
                errors["host_and_data"].append("Only the host id or host address must be provided, not both.")
            elif "host" in data:
                # Check host exists
                if not ManagedHost.objects.filter(id=data["host"]).exists():
                    errors["host"].append("Host of id %s must exist" % data["host"])
            else:
                if "address" in data:
                    # TODO: validate URI
                    host_must_exist = data.get("host_must_exist", None)
                    address = data["address"]

                    if (host_must_exist != None) and (
                        host_must_exist != ManagedHost.objects.filter(address=address).exists()
                    ):
                        errors["address"].append(
                            "Host %s is %s in use by IML" % (address, "not" if host_must_exist else "already")
                        )
                else:
                    errors["address"].append(self.mandatory_message)

        return errors


class HostTestValidation(HostValidation):
    def is_valid(self, bundle, request=None):
        errors = super(HostTestValidation, self).is_valid(bundle, request)

        try:
            auth_type = bundle.data["auth_type"]
            if auth_type == "id_password_root":
                try:
                    root_password = bundle.data["root_password"]
                except KeyError:
                    errors["root_password"].append(self.mandatory_message)
                else:
                    if not len(root_password.strip()):
                        errors["root_password"].append(self.mandatory_message)
            elif auth_type == "private_key_choice":
                try:
                    private_key = bundle.data["private_key"]
                except KeyError:
                    errors["private_key"].append(self.mandatory_message)
                else:
                    if not len(private_key.strip()):
                        errors["private_key"].append(self.mandatory_message)
        except KeyError:
            #  What?  Now auth_type? assume existing key default case.
            pass

        return errors


def _host_params(data, address=None):
    return {
        "address": data.get("address", address),
        "root_pw": data.get("root_password"),
        "pkey": data.get("private_key"),
        "pkey_pw": data.get("private_key_passphrase"),
    }


class ServerProfileResource(ChromaModelResource):
    class Meta:
        queryset = ServerProfile.objects.all()
        resource_name = "server_profile"
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        ordering = ["managed", "default"]
        list_allowed_methods = ["get"]
        readonly = ["ui_name"]
        filtering = {
            "name": ["exact"],
            "managed": ["exact"],
            "worker": ["exact"],
            "default": ["exact"],
            "user_selectable": ["exact"],
        }


class ClientMountResource(ChromaModelResource):
    # This resource is only used for integration testing.

    host = fields.ToOneField("chroma_api.host.HostResource", "host")
    filesystem = fields.ToOneField("chroma_api.filesystem.FilesystemResource", "filesystem")
    mountpoint = fields.CharField()

    class Meta:
        queryset = LustreClientMount.objects.all()
        resource_name = "client_mount"
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        list_allowed_methods = ["get", "post"]

        filtering = {"host": ["exact"], "filesystem": ["exact"]}

    def prepare_mount(self, client_mount):
        return self.alter_detail_data_to_serialize(None, self.full_dehydrate(self.build_bundle(obj=client_mount))).data

    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request
        host = self.fields["host"].hydrate(bundle).obj
        filesystem = self.fields["filesystem"].hydrate(bundle).obj
        mountpoint = bundle.data["mountpoint"]

        client_mount = JobSchedulerClient.create_client_mount(host, filesystem, mountpoint)

        args = dict(client_mount=self.prepare_mount(client_mount))
        raise custom_response(self, request, http.HttpAccepted, args)


class HostResource(MetricResource, StatefulModelResource, BulkResourceOperation, LongPollingAPI):
    """
    Represents a Lustre server that is being monitored and managed from the manager server.

    PUTs to this resource must have the ``state`` attribute set.

    POSTs to this resource must have the ``address`` attribute set.
    """

    nids = fields.ListField(null=True)
    member_of_active_filesystem = fields.BooleanField()
    client_mounts = fields.ListField(null=True)
    root_pw = fields.CharField(help_text="ssh root password to new server.")
    private_key = fields.CharField(help_text="ssh private key matching a " "public key on the new server.")
    private_key_passphrase = fields.CharField(help_text="passphrase to " "decrypt private key")

    server_profile = fields.ToOneField(ServerProfileResource, "server_profile", full=True)

    lnet_configuration = fields.ToOneField(
        "chroma_api.lnet_configuration.LNetConfigurationResource", "lnet_configuration", full=False
    )

    corosync_configuration = fields.ToOneField(
        "chroma_api.corosync.CorosyncConfigurationResource", "corosync_configuration", null=True, full=False
    )

    pacemaker_configuration = fields.ToOneField(
        "chroma_api.pacemaker.PacemakerConfigurationResource", "pacemaker_configuration", null=True, full=False
    )

    # Long polling should return when any of the tables below changes or has changed.
    long_polling_tables = [LNetConfiguration, NetworkInterface, ServerProfile, ManagedFilesystem, ManagedHost]

    def dispatch(self, request_type, request, **kwargs):
        return self.handle_long_polling_dispatch(request_type, request, **kwargs)

    def dehydrate_nids(self, bundle):
        return [n.nid_string for n in Nid.objects.filter(lnet_configuration=bundle.obj.lnet_configuration)]

    def dehydrate_member_of_active_filesystem(self, bundle):
        return bundle.obj.member_of_active_filesystem

    def dehydrate_client_mounts(self, bundle):
        from chroma_core.lib.cache import ObjectCache
        from chroma_core.models import LustreClientMount

        search = lambda cm: cm.host == bundle.obj
        mounts = ObjectCache.get(LustreClientMount, search)
        return [
            {"filesystem_name": mount.filesystem.name, "mountpoint": mount.mountpoint, "state": mount.state}
            for mount in mounts
        ]

    class Meta:
        queryset = ManagedHost.objects.select_related("lnet_configuration").prefetch_related(
            "lnet_configuration__nid_set"
        )
        resource_name = "host"
        excludes = ["not_deleted"]
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        ordering = ["fqdn"]
        list_allowed_methods = ["get", "post", "put"]
        detail_allowed_methods = ["get", "put", "delete"]
        readonly = [
            "nodename",
            "fqdn",
            "nids",
            "member_of_active_filesystem",
            "needs_update",
            "boot_time",
            "client_mounts",
        ]
        # HYD-2256: remove these fields when other auth schemes work
        readonly += ["root_pw", "private_key_passphrase", "private_key"]
        validation = HostValidation()
        always_return_data = True

        filtering = {"id": ["exact"], "fqdn": ["exact", "startswith"], "role": ["exact"]}

    def put_list(self, request, **kwargs):
        """
        based on tastypie/resources.py but modified to do what we actually want!

        Up a collection of resources with another collection.

        Calls ``delete_list`` to clear out the collection then ``obj_create``
        with the provided the data to create the new collection.

        Return ``HttpNoContent`` (204 No Content) if
        ``Meta.always_return_data = False`` (default).

        Return ``HttpAccepted`` (202 Accepted) if
        ``Meta.always_return_data = True``.
        """
        deserialized = self.deserialize(
            request, request.raw_post_data, format=request.META.get("CONTENT_TYPE", "application/json")
        )
        deserialized = self.alter_deserialized_list_data(request, deserialized)

        if not "objects" in deserialized:
            raise http.HttpBadRequest("Invalid data sent.")

        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)

        self.obj_update(bundle, **kwargs)

    @validate
    def obj_update(self, bundle, **kwargs):
        def _update_action(self, data, request, **kwargs):
            # For simplicity lets fake the kwargs if we can, this is for when we are working from objects
            if "address" in data:
                host = ManagedHost.objects.get(address=data["address"])
            elif "pk" in kwargs:
                host = self.cached_obj_get(
                    self.build_bundle(data=data, request=request), **self.remove_api_resource_names(kwargs)
                )
            else:
                return self.BulkActionResult(None, "Unable to decipher target host", None)

            # If the host that is being updated is in the undeployed state then this is a special case and the normal
            # state change doesn't work because we need to provide some parameters to the allow the ssh connection to
            # bootstrap the agent into existence.
            if host.state == "undeployed":
                return self._create_host(host.address, data, request)
            else:
                if "pk" in kwargs:
                    try:
                        super(HostResource, self).obj_update(self.build_bundle(data=data, request=request), **kwargs)
                        return self.BulkActionResult(None, "State data not present for host %s" % host, None)
                    except ImmediateHttpResponse as ihr:
                        if int(ihr.response.status_code / 100) == 2:
                            return self.BulkActionResult(json.loads(ihr.response.content), None, None)
                        else:
                            return self.BulkActionResult(None, json.loads(ihr.response.content), None)
                else:
                    return self.BulkActionResult(None, "Bulk setting of state not yet supported", None)

        self._bulk_operation(_update_action, "command_and_host", bundle, bundle.request, **kwargs)

    @validate
    def obj_create(self, bundle, **kwargs):
        # FIXME HYD-1657: we get errors back just fine when something goes wrong
        # during registration, but the UI tries to format backtraces into
        # a 'validation errors' dialog which is pretty ugly.
        if bundle.data.get("failed_validations"):
            log.warning(
                "Attempting to create host %s after failed validations: %s"
                % (bundle.data.get("address"), bundle.data.get("failed_validations"))
            )

        def _update_action(self, data, request, **kwargs):
            return self._create_host(None, data, request)

        self._bulk_operation(_update_action, "command_and_host", bundle, bundle.request, **kwargs)

    def _create_host(self, address, data, request):
        # Resolve a server profile URI to a record
        profile = ServerProfileResource().get_via_uri(data["server_profile"], request)

        host, command = JobSchedulerClient.create_host_ssh(server_profile=profile.name, **_host_params(data, address))

        #  TODO:  Could simplify this by adding a 'command' key to the
        #  bundle, then optionally handling dehydrating that
        #  in super.alter_detail_data_to_serialize.  That way could
        #  return from this method avoiding all this extra code, and
        #  providing a central handling for all things that migth have
        #  a command argument.  NB:  not tested, and not part of any ticket
        object = {
            "command": dehydrate_command(command),
            "host": self.alter_detail_data_to_serialize(None, self.full_dehydrate(self.build_bundle(obj=host))).data,
        }

        return self.BulkActionResult(object, None, None)

    def apply_filters(self, request, filters=None):
        objects = super(HostResource, self).apply_filters(request, filters)
        try:
            try:
                fs = ManagedFilesystem.objects.get(pk=request.GET["filesystem_id"])
            except ManagedFilesystem.DoesNotExist:
                objects = objects.filter(id=-1)  # No filesystem so we want to produce an empty list.
            else:
                objects = objects.filter(
                    (
                        Q(managedtargetmount__target__managedmdt__filesystem=fs)
                        | Q(managedtargetmount__target__managedost__filesystem=fs)
                    )
                    | Q(managedtargetmount__target__id=fs.mgs.id)
                )
        except KeyError:
            # Not filtering on filesystem_id
            pass

        # convenience filter for the UI client
        if request.GET.get("worker", False):
            objects = objects.filter(server_profile__worker=True)

        try:
            from chroma_api.target import KIND_TO_MODEL_NAME

            server_role = request.GET["role"].upper()
        except KeyError:
            # No 'role' argument
            pass
        else:
            target_model = KIND_TO_MODEL_NAME["%sT" % server_role[:-1]]
            objects = objects.filter(
                Q(managedtargetmount__target__content_type__model=target_model)
                & Q(managedtargetmount__target__not_deleted=True)
            )

        return objects.distinct()


class HostTestResource(Resource, BulkResourceOperation):
    """
    A request to test a potential host address for accessibility, typically
    used prior to creating the host.  Only supports POST with the 'address'
    field.

    """

    address = fields.CharField(help_text="Same as ``address`` " "field on host resource.")

    server_profile = fields.CharField(help_text="Server profile chosen")

    root_pw = fields.CharField(help_text="ssh root password to new server.")
    private_key = fields.CharField(help_text="ssh private key matching a " "public key on the new server.")
    private_key_passphrase = fields.CharField(help_text="passphrase to " "decrypt private key")

    auth_type = fields.CharField(
        help_text="SSH authentication type. "
        "If has the value 'root_password_choice', then the root_password "
        "field must be non-empty, and if the value is 'private_key_choice' "
        "then the private_key field must be non empty.  All other values are "
        "ignored and assume existing private key.  This field is not for "
        "actual ssh connections.  It is used to validate that enough "
        "information is available to attempt the chosen auth_type."
    )

    class Meta:
        list_allowed_methods = ["post"]
        detail_allowed_methods = []
        resource_name = "test_host"
        authentication = AnonymousAuthentication()
        authorization = PermissionAuthorization("chroma_core.add_managedhost")
        object_class = dict
        validation = HostTestValidation()

    @validate
    def obj_create(self, bundle, **kwargs):
        def _test_host_contact(self, data, request, **kwargs):
            return self.BulkActionResult(
                dehydrate_command(JobSchedulerClient.test_host_contact(**_host_params(data))), None, None
            )

        self._bulk_operation(_test_host_contact, "command", bundle, bundle.request, **kwargs)


class HostProfileResource(Resource, BulkResourceOperation):
    """
    Get and set profiles associated with hosts.
    """

    class Meta:
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "put"]
        resource_name = "host_profile"
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        object_class = dict

    def get_resource_uri(self, bundle_or_obj=None):
        url_name = "api_dispatch_list"

        if bundle_or_obj is not None:
            url_name = "api_dispatch_detail"

        kwargs = {"resource_name": self._meta.resource_name, "api_name": self._meta.api_name}

        if isinstance(bundle_or_obj, Bundle):
            kwargs["pk"] = bundle_or_obj.obj.id
        elif bundle_or_obj is not None:
            kwargs["pk"] = bundle_or_obj.id

        return self._build_reverse_url(url_name, kwargs=kwargs)

    def full_dehydrate(self, bundle, for_list=False):
        return bundle.obj

    HostProfiles = namedtuple("HostProfiles", ["profiles", "valid"])

    def get_profiles(self, host, request):
        properties = json.loads(host.properties)

        filters = {}
        for filter in request.GET:
            match = re.search("^server_profile__(.*)", filter)
            if match:
                filters[match.group(1)] = request.GET[filter]

        result = {}
        for profile in ServerProfile.objects.filter(**filter_fields_to_type(ServerProfile, filters)):
            tests = result[profile.name] = []
            for validation in profile.serverprofilevalidation_set.all():
                error = ""

                if properties == {}:
                    test = False
                    error = "Result unavailable while host agent starts"
                else:
                    try:
                        test = safe_eval(validation.test, properties)
                    except Exception as error:
                        test = False

                tests.append(
                    {
                        "pass": bool(test),
                        "test": validation.test,
                        "description": validation.description,
                        "error": str(error),
                    }
                )
        return self.HostProfiles(result, properties != {})

    def _set_profile(self, host_id, profile):
        server_profile = get_object_or_404(ServerProfile, pk=profile)

        commands = []

        host = ManagedHost.objects.get(pk=host_id)

        if host.server_profile.name != profile:
            command = JobSchedulerClient.set_host_profile(host.id, server_profile.id)

            if command:
                commands.append(command)

            if server_profile.initial_state in host.get_available_states(host.state):
                commands.append(Command.set_state([(host, server_profile.initial_state)]))

        return map(dehydrate_command, commands)

    def _host_profiles_object(self, host, request):
        host_profiles = self.get_profiles(host, request)

        return {
            "host": host.id,
            "address": host.address,
            "profiles_valid": host_profiles.valid,
            "profiles": host_profiles.profiles,
            "resource_uri": self.get_resource_uri(host),
        }

    def obj_get(self, bundle, pk=None):
        host = get_object_or_404(ManagedHost, pk=pk)

        return self._host_profiles_object(host, bundle.request)

    def obj_get_list(self, bundle):
        ids = bundle.request.GET.getlist("id__in")
        filters = {"id__in": ids} if ids else {}

        result = []

        for host in ManagedHost.objects.filter(**filters):
            result.append(
                {"host_profiles": self._host_profiles_object(host, bundle.request), "error": None, "traceback": None}
            )

        return result

    @validate
    def obj_create(self, bundle, **kwargs):
        def _create_action(self, data, request, **kwargs):
            return self.BulkActionResult(self._set_profile(data["host"], data["profile"]), None, None)

        self._bulk_operation(_create_action, "commands", bundle, bundle.request, **kwargs)

    @validate
    def obj_update(self, bundle, **kwargs):
        def _update_action(self, data, request, **kwargs):
            return self.BulkActionResult(self._set_profile(kwargs["pk"], data["profile"]), None, None)

        self._bulk_operation(_update_action, "commands", bundle, bundle.request, **kwargs)
