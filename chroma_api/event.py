#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models.event import Event
import logging

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
import tastypie.constants

STR_TO_SEVERITY = dict([(logging.getLevelName(level), level) for level in [
    logging.INFO,
    logging.ERROR,
    logging.CRITICAL,
    logging.WARNING,
    logging.DEBUG
    ]])


class EventResource(ModelResource):
    host_name = fields.CharField()
    host = fields.ToOneField('chroma_api.host.HostResource', 'host', null = True)
    message = fields.CharField()

    class Meta:
        queryset = Event.objects.all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        filtering = {
                'severity': ['exact'],
                'host': tastypie.constants.ALL_WITH_RELATIONS,
                }

    def dehydrate_host_name(self, bundle):
        return bundle.obj.host.pretty_name() if bundle.obj.host else "---"

    def dehydrate_message(self, bundle):
        return bundle.obj.message()

    def dehydrate_severity(self, bundle):
        return logging.getLevelName(bundle.obj.severity)

    def build_filters(self, filters = None):
        custom_filters = {}
        severity = filters.get('severity', None)
        event_type = filters.get('event_type', None)

        if severity != None:
            del filters['severity']
            if severity:
                filters['severity'] = STR_TO_SEVERITY[severity]

        if event_type:
            del filters['event_type']
            custom_filters['content_type__model'] = event_type.lower()

        filters = super(EventResource, self).build_filters(filters)
        filters.update(custom_filters)
        return filters
