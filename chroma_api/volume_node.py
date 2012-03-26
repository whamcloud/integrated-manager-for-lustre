#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import LunNode
from tastypie.resources import ModelResource

from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication

from tastypie import fields


class VolumeNodeResource(ModelResource):
    """
    Represents a device node on a particular host, which
    accesses a particular volume.  Usually accessed
    as an attribute of a volume rather than on its own.

    This resource cannot be written to directly.  To update
    ``use`` and ``primary``, PUT to the volume that the
    node belongs to.
    """

    volume_id = fields.IntegerField(attribute = 'lun_id',
            help_text = "id of the volume that this node belongs to")
    host_id = fields.IntegerField(help_text = "id if the host that this\
            device node is on")
    host_label = fields.CharField(help_text = "label attribute of the \
            host that this device node is on, as a convenience \
            for presentation")

    def dehydrate_host_id(self, bundle):
        return bundle.obj.host.id

    def dehydrate_host_label(self, bundle):
        return bundle.obj.host.get_label()

    class Meta:
        queryset = LunNode.objects.filter(host__not_deleted = True)
        resource_name = 'volume_node'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['not_deleted', 'lun_id']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
