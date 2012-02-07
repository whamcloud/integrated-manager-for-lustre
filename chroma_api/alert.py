#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models.alert import AlertState

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication


class AlertResource(ModelResource):
    message = fields.CharField(readonly = True)
    alert_item_str = fields.CharField(readonly = True)

    class Meta:
        queryset = AlertState.objects.all()
        resource_name = 'alert'
        fields = ['begin', 'end', 'message', 'active', 'alert_item']
        filtering = {'active': ['exact']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()

    def dehydrate_message(self, bundle):
        return bundle.obj.message()

    def dehydrate_alert_item_str(self, bundle):
        return str(bundle.obj.alert_item)
