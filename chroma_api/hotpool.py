# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from tastypie import fields, http
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.utils import custom_response, dehydrate_command, StatefulModelResource
from chroma_api.validation_utils import validate
from chroma_core.models.command import Command
from chroma_core.models.hotpools import HotpoolConfiguration, LamigoConfiguration, LpurgeConfiguration
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

from chroma_core.models.filesystem import ManagedFilesystem, OstPool


class HotpoolValidation(Validation):
    def _validate_post(self, bundle, request):
        errors = defaultdict(list)

        for mandatory_field in ["filesystem", "hotpool", "coldpool", "freehi", "freelo", "minage"]:
            if mandatory_field not in bundle.data or bundle.data[mandatory_field] == None:
                errors[mandatory_field].append("This field is mandatory")

        fs_id = bundle.data["filesystem"]
        try:
            fs = ManagedFilesystem.objects.get(id=fs_id)
        except Volume.DoesNotExist:
            errors["filesystem"].append("Filesystem %s not found" % fs_id)

        for pool_field in ["hotpool", "coldpool"]:
            pool_id = bundle.data[pool_field]
            try:
                pool = OstPool.objects.get(id=pool_id)
            except OstPool.DoesNotExist:
                errors[pool_field].append("OstPool %s not found" % pool_id)
            else:
                if pool.filesystem != fs:
                    errors[pool_field].append("OstPool %s not part of fs %s" % (pool_id, fs_id))
        return errors

    def is_valid(self, bundle, request=None):
        if request.method == "POST":
            return self._validate_post(bundle, request)
        # elif request.method == "PUT":
        #    return self._validate_put(bundle, request)
        else:
            return {}


class HotpoolResource(StatefulModelResource):
    filesystem = fields.ToOneField("chroma_api.filesystem.FilesystemResource", "filesystem")
    #hotpool = fields.ToOneField("chroma_api.filesystem.OstPoolResource", "hotpool")
    #coldpool = fields.ToOneField("chroma_api.filesystem.OstPoolResource", "coldpool")

    # @@ lamigo/lpurge

    class Meta:
        queryset = HotpoolConfiguration.objects.all()
        resource_name = "hotpool"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted"]
        ordering = ["name"]
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "put", "delete"]
        filtering = {"filesystem": ["exact"], "name": ["exact"], "id": ["exact"]}
        validation = HotpoolValidation()

    # POST
    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        hotpool_id, command_id = JobSchedulerClient.create_hotpool(bundle.data)
        command = Command.objects.get(pk=command_id)

        raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})

    # DELETE handler
    def obj_delete(self, bundle, **kwargs):
        request = bundle.request
        try:
            obj = self.obj_get(bundle, **kwargs)
            command_id = JobSchedulerClient.remove_hotpool(obj.id)
            command = Command.objects.get(pk=command_id)

        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})
