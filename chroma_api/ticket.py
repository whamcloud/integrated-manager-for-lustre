# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.contrib.contenttypes.models import ContentType
from tastypie import fields
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.host import HostResource
from chroma_core.models.ticket import FilesystemTicket, MasterTicket, Ticket

KIND_TO_KLASS = {"Master": MasterTicket, "Filesystem": FilesystemTicket}
KLASS_TO_KIND = dict([(v, k) for k, v in KIND_TO_KLASS.items()])
KIND_TO_MODEL_NAME = dict([(k, v.__name__.lower()) for k, v in KIND_TO_KLASS.items()])


class TicketResource(ChromaModelResource):
    kind = fields.CharField(help_text="Type of ticket, one of %s" % KIND_TO_KLASS.keys())
    related_uri = fields.CharField()

    def content_type_id_to_kind(self, ct_id):
        if not hasattr(self, "CONTENT_TYPE_ID_TO_KIND"):
            self.CONTENT_TYPE_ID_TO_KIND = dict(
                [(ContentType.objects.get_for_model(v).id, k) for k, v in KIND_TO_KLASS.items()]
            )

        return self.CONTENT_TYPE_ID_TO_KIND[ct_id]

    def dehydrate_kind(self, bundle):
        return self.content_type_id_to_kind(bundle.obj.content_type_id)

    def dehydrate_related_uri(self, bundle):
        target = bundle.obj.downcast()
        if isinstance(target, FilesystemTicket):
            from chroma_api.filesystem import FilesystemResource

            return FilesystemResource().get_resource_uri(target.filesystem)

        if isinstance(target, MasterTicket):
            from chroma_api.target import TargetResource

            return TargetResource().get_resource_uri(target.mgs)

    class Meta:
        queryset = Ticket.objects.select_related("masterticket", "filesystemticket").all()
        resource_name = "ticket"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted"]
        ordering = ["name"]
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get"]
        filtering = {"name": ["exact"], "id": ["exact"]}
