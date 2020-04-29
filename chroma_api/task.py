# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import tastypie.http as http
from tastypie import fields

from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.utils import custom_response, dehydrate_command

from chroma_core.models import Task


class TaskResource(ChromaModelResource):
    filesystem = fields.ToOneField("chroma_api.filesystem.FilesystemResource", "filesystem")
    running_on = fields.ToOneField("chroma_api.host.ManagedHost", "running_on", null=True, blank=True)

    class Meta:
        queryset = Task.objects.all()
        resource_name = "task"
        authentication = AnonymousAuthentication()
        authorization = PatchedDjangoAuthorization()
        ordering = ["name", "filesystem"]
        list_allowed_methods = ["get", "delete", "put", "post"]
        detail_allowed_methods = ["get", "put", "delete"]
        filtering = {"filesystem": ["exact"], "name": ["exact"], "id": ["exact"]}

    # POST handler
    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        ostpool_id, command_id = JobSchedulerClient.create_task(bundle.data)
        command = Command.objects.get(pk=command_id)

        raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})
