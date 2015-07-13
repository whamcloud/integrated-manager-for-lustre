#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import logging

from tastypie.fields import CharField, DateTimeField, IntegerField, BooleanField

from django.db.models.query import QuerySet
from django.db.models import fields as django_fields

from chroma_api.authentication import CsrfAuthentication
from tastypie.utils import trailing_slash
from tastypie.api import url
from tastypie import http
from tastypie.authorization import Authorization
from tastypie.resources import Resource, ModelResource

from chroma_api.alert import AlertResource
from chroma_api.event import EventResource
from chroma_api.command import CommandResource
from chroma_core.models import Command, AlertState, Event


class SortableList(list):
    def order_by(self, *order_by_args):
        for sort in reversed(order_by_args):
            reverse = sort.startswith('-')

            if reverse:
                sort = sort[1:]

            self.sort(key = lambda x: getattr(x, sort), reverse = reverse)

        return self


class NotificationResource(Resource):
    """Notification API endpoint
    A notification is a general term for an Alert, Event or Command, any of which
    can be thought of as a notification in this context.
    """

    id = IntegerField('id')
    message = CharField(attribute = 'message')
    dismissed = BooleanField('dismissed')
    severity = CharField(attribute = 'severity', null = True)
    created_at = DateTimeField(attribute = 'created_at')
    type = CharField(attribute = 'type', null = True)
    subtype = CharField(attribute = 'subtype', null = True)

    class Meta:
        authentication = CsrfAuthentication()
        authorization = Authorization()
        list_allowed_methods = ['get']
        detail_allowed_methods = []
        fields = ['id', 'message', 'severity', 'dismissed', 'created_at', 'type', 'subtype']
        ordering = fields
        resource_name = 'notification'
        ordering = fields
        filtering = {'id': ['exact', 'in'],
                     'dismissed': ['exact'],
                     'created_at': ['gte']}

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/dismiss_all%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('dismiss_all'), name='api_notification_dismiss_all'),
        ]

    # The purpose of this function is to request the objects in their base form, many objects will downcast
    # themselves as they are iterated and this is slow because each iteration is a db query. This routine
    # returns the base object.
    # The routine does some basic sorting and throws FieldError for confusion which means the real and slow
    # tastypie routines can take over.
    def _base_objects(self, klass, request, **kwargs):
        try:
            reserved_fields = ['order_by', 'format', 'limit', 'offset']

            q = QuerySet(klass._meta.object_class)

            query = dict(request.REQUEST)

            fields = {}
            for field in q.model._meta.fields:
                fields[field.column] = field

            # Remove the reserved fields we know about.
            for field in query.keys():
                if field in reserved_fields:
                    del query[field]

            # This will error if it find an unknown field and cause the standard tasty pie query to run.
            for field in query.keys():
                field_type = type(fields[field])
                value = query[field]

                if field_type == django_fields.AutoField or field_type == django_fields.IntegerField:
                    value = int(value)
                elif field_type == django_fields.BooleanField:
                    value = (value.lower() == 'true')

                query[field] = value

            return list(q.filter(**query))
        except KeyError:
            return list(klass().obj_get_list(request, **kwargs))

    def obj_get_list(self, request=None, **kwargs):
        return SortableList(self._base_objects(AlertResource, request, **kwargs) +
                            self._base_objects(EventResource, request, **kwargs) +
                            self._base_objects(CommandResource, request, **kwargs))

    def dismiss_all(self, request, **kwargs):
        if (request.method != 'PUT') or (not request.user.is_authenticated()):
            return http.HttpUnauthorized()

        # Uses authentication etc from the resource below.
        AlertResource().dismiss_all(request, **kwargs)
        EventResource().dismiss_all(request, **kwargs)
        CommandResource().dismiss_all(request, **kwargs)

        return http.HttpNoContent()

    def _to_resource_class(self, obj_klass):
        for klass, resource in {Command: CommandResource,
                                AlertState: AlertResource,
                                Event: EventResource}.items():

            if issubclass(obj_klass, klass):
                return resource

        raise TypeError('type %s is not understood by the NotificationsResource' % obj_klass)

    def full_dehydrate(self, bundle):
        if hasattr(bundle.obj, 'downcast'):
            bundle.obj = bundle.obj.downcast()              # Cast it into what we actually want.

        resource_class = self._to_resource_class(type(bundle.obj))

        # Do any unique ones fields like type
        super(NotificationResource, self).full_dehydrate(bundle)

        # Then do the specific type ones.
        return getattr(resource_class(), 'full_dehydrate')(bundle)

    def dehydrate_type(self, bundle):
        if type(bundle.obj).__name__ == 'Command':
            #  Command is the type
            return 'Command'
        else:
            #  Otherwise, either AlertState and Event superclass
            return type(bundle.obj).__bases__[0].__name__

    def dehydrate_subtype(self, bundle):
        if type(bundle.obj).__name__ != 'Command':
            return type(bundle.obj).__name__
        else:
            return None

    def dehydrate_severity(self, bundle):
        try:
            #  Alerts and Events have a severity attribute
            return logging.getLevelName(bundle.obj.severity)
        except AttributeError:
            #  Assuming a Command, which does not have a severity attribute
            #  But, if errored, that is considered ERROR level severity
            if bundle.obj.errored:
                return logging.getLevelName(40)
            else:
                return logging.getLevelName(20)

    def dehydrate_resource_uri(self, bundle):
        return self._to_resource_class(type(bundle.obj))().get_resource_uri(bundle.obj)

    def apply_sorting(self, obj_list, options=None):
        # Bit of a cheat, Resource does not have a default sorting implementation but ModelResource does
        # and is used by all the Resources we are simulating.
        # Make a simple ModelResource so that we can use its code and stuff it with out _meta data.
        model_resource = ModelResource()
        model_resource._meta = self._meta
        model_resource.fields = self.fields

        return model_resource.apply_sorting(obj_list, options)
