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
    volume_id = fields.IntegerField(attribute = 'lun_id')
    host_id = fields.IntegerField()
    host_label = fields.CharField()

    def dehydrate_host_id(self, bundle):
        return bundle.obj.host.id

    def dehydrate_host_label(self, bundle):
        return bundle.obj.host.get_label()

    class Meta:
        queryset = LunNode.objects.all()
        resource_name = 'volume_node'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['not_deleted', 'lun_id']
