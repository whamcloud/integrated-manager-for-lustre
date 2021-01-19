# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.models import VolumeNode

from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource

from tastypie import fields


class VolumeNodeResource(ChromaModelResource):
    """
    Represents a device node on a particular host, which
    accesses a particular volume.  Usually accessed
    as an attribute of a volume rather than on its own.

    This resource cannot be written to directly.  To update
    ``use`` and ``primary``, PUT to the volume that the
    node belongs to.

    This resource is used by the CLI
    """

    volume_id = fields.IntegerField(attribute="volume_id", help_text="id of the volume that this node belongs to")
    host_id = fields.IntegerField(
        help_text="id of the host that this\
            device node is on"
    )
    host_label = fields.CharField(
        help_text="label attribute of the \
            host that this device node is on, as a convenience \
            for presentation"
    )
    host = fields.ToOneField("chroma_api.host.HostResource", "host")

    def dehydrate_host_id(self, bundle):
        return bundle.obj.host.id

    def dehydrate_host_label(self, bundle):
        return bundle.obj.host.get_label()

    class Meta:
        queryset = VolumeNode.objects.all().select_related("host")
        resource_name = "volume_node"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["not_deleted"]
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get"]
        filtering = {"host": ["exact"], "path": ["exact"]}
