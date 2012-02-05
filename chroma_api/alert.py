#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from monitor.models import AlertState

from tastypie.resources import ModelResource
from tastypie import fields


class AlertResource(ModelResource):
    message = fields.CharField(readonly = True)
    alert_item_str = fields.CharField(readonly = True)

    class Meta:
        queryset = AlertState.objects.all()
        resource_name = 'alert'
        fields = ['begin', 'end', 'message', 'active', 'alert_item']
        filtering = {'active': ['exact']}

    def dehydrate_message(self, bundle):
        return bundle.obj.message()

    def dehydrate_alert_item_str(self, bundle):
        return str(bundle.obj.alert_item)
