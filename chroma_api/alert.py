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
    """
    A bad health state.  Alerts refer to particular objects (such as
    servers or targets), and can either be active (this is a current
    problem) or inactive (this is a historical record of a problem).

    The ``alert_item_content_type_id`` and ``alert_item_id`` attributes
    together provide a unique reference to the object to which the
    alert refers.
    """
    message = fields.CharField(readonly = True, help_text = "Human readable description\
            of the alert, about one sentence")
    alert_item_content_type_id = fields.IntegerField()
    active = fields.BooleanField(help_text = "True if the alert is a current issue, false\
            if it is historical")

    def dehydrate_alert_item_content_type_id(self, bundle):
        return bundle.obj.alert_item_type.id

    alert_item_str = fields.CharField(readonly = True,
            help_text = "A human readable noun describing the object\
            that is the subject of the alert")

    class Meta:
        queryset = AlertState.objects.all()
        resource_name = 'alert'
        fields = ['begin', 'end', 'message', 'active', 'alert_item_id', 'alert_item_content_type_id']
        filtering = {'active': ['exact']}
        ordering = ['begin', 'end', 'active']
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']

    def dehydrate_message(self, bundle):
        return bundle.obj.message()

    def dehydrate_alert_item_str(self, bundle):
        return str(bundle.obj.alert_item)
