# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.models import ManagedOst, ManagedMdt
from chroma_core.models import Command, OstPool

import tastypie.http as http
from tastypie import fields
from tastypie.exceptions import NotFound
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.utils import custom_response, ConfParamResource, dehydrate_command
from chroma_api.validation_utils import validate
from chroma_core.lib import conf_param


class FilesystemValidation(Validation):
    def _validate_put(self, bundle, request):
        errors = defaultdict(list)

        if "conf_params" in bundle.data and bundle.data["conf_params"] is not None:
            try:
                fs = ManagedFilesystem.objects.get(pk=bundle.data["id"])
            except ManagedFilesystem.DoesNotExist:
                errors["id"] = "Filesystem with id %s not found" % bundle.data["id"]
            except KeyError:
                errors["id"] = "Field is mandatory"
            else:
                if fs.immutable_state:
                    if not conf_param.compare(bundle.data["conf_params"], conf_param.get_conf_params(fs)):
                        errors["conf_params"].append("Cannot modify conf_params on immutable_state objects")
                else:
                    conf_param_errors = conf_param.validate_conf_params(ManagedFilesystem, bundle.data["conf_params"])
                    if conf_param_errors:
                        errors["conf_params"] = conf_param_errors

        return errors

    def is_valid(self, bundle, request=None):
        if request.method == "PUT":
            return self._validate_put(bundle, request)
        else:
            return {}


class FilesystemResource(ConfParamResource):
    """
    A Lustre file system, associated with exactly one MGT and consisting of
    one or mode MDTs and one or more OSTs.

    When using POST to create a file system, specify volumes to use like this:
    ::

        {osts: [{volume_id: 22}],
        mdt: {volume_id: 23},
        mgt: {volume_id: 24}}

    To create a file system using an existing MGT instead of creating a new
    MGT, set the `id` attribute instead of the `volume_id` attribute for
    that target (i.e. `mgt: {id: 123}`).

    Note: A Lustre file system is owned by an MGT, and the ``name`` of the file system
    is unique within that MGT.  Do not use ``name`` as a globally unique identifier
    for a file system in your application.
    """

    osts = fields.ToManyField(
        "chroma_api.target.TargetResource",
        null=True,
        attribute=lambda bundle: ManagedOst.objects.filter(filesystem=bundle.obj),
        help_text="List of OSTs which belong to this file system",
    )
    mdts = fields.ToManyField(
        "chroma_api.target.TargetResource",
        null=True,
        attribute=lambda bundle: ManagedMdt.objects.filter(filesystem=bundle.obj),
        help_text="List of MDTs in this file system, should be at least 1 unless the "
        "file system is in the process of being deleted",
    )
    mgt = fields.ToOneField(
        "chroma_api.target.TargetResource",
        attribute="mgs",
        help_text="The MGT on which this file system is registered",
    )

    class Meta:
        queryset = ManagedFilesystem.objects.all()
        resource_name = "filesystem"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted", "ost_next_index", "mdt_next_index"]
        ordering = ["name"]
        filtering = {"id": ["exact", "in"], "name": ["exact"]}
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get", "delete", "put"]
        validation = FilesystemValidation()
        always_return_data = True


class OstPoolResource(ChromaModelResource):
    osts = fields.ToManyField(
        "chroma_api.target.TargetResource",
        "osts",
        null=True,
        help_text="List of OSTs in this Pool",
    )
    filesystem = fields.ToOneField("chroma_api.filesystem.FilesystemResource", "filesystem")

    class Meta:
        queryset = OstPool.objects.all()
        resource_name = "ostpool"
        authentication = AnonymousAuthentication()
        authorization = PatchedDjangoAuthorization()
        excludes = ["not_deleted"]
        ordering = ["filesystem", "name"]
        list_allowed_methods = ["get", "delete", "put"]
        detail_allowed_methods = ["get", "put", "delete"]
        filtering = {"filesystem": ["exact"], "name": ["exact"], "id": ["exact"]}

    # POST handler
    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        ostpool_id, command_id = JobSchedulerClient.create_ostpool(bundle.data)
        command = Command.objects.get(pk=command_id)

        raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})

    # PUT handler
    @validate
    def obj_update(self, bundle, **kwargs):
        try:
            obj = self.obj_get(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        command_id = JobSchedulerClient.update_ostpool(bundle.data)
        command = Command.objects.get(pk=command_id)

        raise custom_response(self, bundle.request, http.HttpAccepted, {"command": dehydrate_command(command)})

    # DELETE handlers
    def _pool_delete(self, request, obj_list):
        commands = []
        for obj in obj_list:
            command_id = JobSchedulerClient.delete_ostpool(obj.id)
            command = Command.objects.get(pk=command_id)
            commands.append(dehydrate_command(command))
        raise custom_response(self, request, http.HttpAccepted, {"commands": commands})

    def obj_delete(self, bundle, **kwargs):
        try:
            obj = self.obj_get(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")
        self._pool_delete(bundle.request, [obj])

    def obj_delete_list(self, bundle, **kwargs):
        try:
            obj_list = self.obj_get_list(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")
        self._pool_delete(bundle.request, obj_list)
