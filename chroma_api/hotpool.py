# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.contrib.contenttypes.models import ContentType
from tastypie import fields
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.host import HostResource
from chroma_core.models.hotpools import HotpoolConfiguration, LamigoConfiguration, LpurgeConfiguration


class HotpoolResource(ChromaModelResource):
    filesystem = fields.ToOneField("chroma_api.filesystem.FilesystemResource", "filesystem")

    class Meta:
        queryset = HotpoolConfiguration.objects.all()
        resource_name = "hotpool"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted"]
        ordering = ["name"]
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get"]
        filtering = {"filesystem": ["exact"], "name": ["exact"], "id": ["exact"]}

    # POST
    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        hotpool_id, command_id = JobSchedulerClient.create_hotpool(bundle.data)
        command = Command.objects.get(pk=command_id)

        raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})
