# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from collections import defaultdict
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services import log_register
from tastypie.validation import Validation
from tastypie.utils import dict_strip_unicode_keys
from chroma_api.validation_utils import validate

import json

from chroma_core.models.host import ManagedHost
from chroma_core.models.client_mount import LustreClientMount
from chroma_core.models.server_profile import ServerProfile
from chroma_core.models.nid import Nid
from tastypie.exceptions import ImmediateHttpResponse


import tastypie.http as http
from tastypie.resources import Resource
from tastypie import fields
from chroma_api.utils import (
    StatefulModelResource,
    dehydrate_command,
    BulkResourceOperation,
)
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.authentication import PermissionAuthorization
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
                            "Host %s is %s in use" % (address, "not" if host_must_exist else "already")
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
            #  What?  Now auth_type? Assume existing key default case.
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
    repolist = fields.ListField(null=False)

    def dehydrate_repolist(self, bundle):
        return [r for r in bundle.obj.repos]

    class Meta:
        queryset = ServerProfile.objects.all()
        resource_name = "server_profile"
        authentication = AnonymousAuthentication()
        authorization = PatchedDjangoAuthorization()
        ordering = ["managed", "default"]
        list_allowed_methods = ["get"]
        readonly = ["ui_name", "repolist"]
        filtering = {
            "name": ["exact"],
            "managed": ["exact"],
            "worker": ["exact"],
            "default": ["exact"],
            "user_selectable": ["exact"],
        }


class ClientMountResource(ChromaModelResource):
    host = fields.ToOneField("chroma_api.host.HostResource", "host")
    filesystem = fields.CharField()
    mountpoint = fields.CharField()

    class Meta:
        queryset = LustreClientMount.objects.all()
        resource_name = "client_mount"
        authentication = AnonymousAuthentication()
        authorization = PatchedDjangoAuthorization()
        list_allowed_methods = ["get", "post"]

        filtering = {"host": ["exact"], "filesystem": ["exact"]}


class HostResource(StatefulModelResource, BulkResourceOperation):
    """
    Represents a Lustre server that is being monitored and managed from the manager server.

    PUTs to this resource must have the ``state`` attribute set.

    POSTs to this resource must have the ``address`` attribute set.
    """

    nids = fields.ListField(null=True)
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

    def dehydrate_nids(self, bundle):
        return [n.nid_string for n in Nid.objects.filter(lnet_configuration=bundle.obj.lnet_configuration)]

    class Meta:
        queryset = ManagedHost.objects.select_related("lnet_configuration").prefetch_related(
            "lnet_configuration__nid_set"
        )
        resource_name = "host"
        excludes = ["not_deleted"]
        authentication = AnonymousAuthentication()
        authorization = PatchedDjangoAuthorization()
        ordering = ["fqdn"]
        list_allowed_methods = ["get", "post", "put"]
        detail_allowed_methods = ["get", "put", "delete"]
        readonly = [
            "nodename",
            "fqdn",
            "nids",
            "needs_update",
            "boot_time",
        ]
        # HYD-2256: remove these fields when other auth schemes work
        readonly += ["root_pw", "private_key_passphrase", "private_key"]
        validation = HostValidation()
        always_return_data = True

        filtering = {"id": ["exact"], "fqdn": ["exact", "startswith"]}

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
            request, request.body, format=request.META.get("CONTENT_TYPE", "application/json")
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

        # convenience filter for the UI client
        if request.GET.get("worker", False):
            objects = objects.filter(server_profile__worker=True)

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
