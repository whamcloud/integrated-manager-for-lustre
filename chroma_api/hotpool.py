# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.contrib.contenttypes.models import ContentType
from tastypie import fields
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.host import HostResource
from chroma_core.models.hotpools import HotpoolConfiguration, HotpoolV2Configuration

KIND_TO_KLASS = {"V2": HotpoolV2Configuration}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])
KIND_TO_MODEL_NAME = dict([(k, v.__name__.lower()) for k, v in KIND_TO_KLASS.items()])


class HotpoolResource(ChromaModelResource):
    kind = fields.CharField(help_text="Hotpool Version, one of %s" % KIND_TO_KLASS.keys())
    related_uri = fields.CharField()

    def content_type_id_to_kind(self, ct_id):
        if not hasattr(self, "CONTENT_TYPE_ID_TO_KIND"):
            self.CONTENT_TYPE_ID_TO_KIND = dict(
                [(ContentType.objects.get_for_model(v).id, k) for k, v in KIND_TO_KLASS.items()]
            )

        return self.CONTENT_TYPE_ID_TO_KIND[ct_id]

    def dehydrate_kind(self, bundle):
        return self.content_type_id_to_kind(bundle.obj.content_type_id)

    class Meta:
        queryset = HotpoolConfiguration.objects.select_related("hotpoolv2configuration").all()
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
