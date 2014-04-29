#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

from tastypie.fields import CharField, DateTimeField

from chroma_api.authentication import CsrfAuthentication
from tastypie.authorization import Authorization
from tastypie.resources import Resource
from chroma_core.models import AlertState, Command, Event


class NotificationResource(Resource):
    """Notification API endpoint

    A notification is a general term for an Alert, Event or Command, any of which
    can be thought of as a notification in this context.
    """

    # TODO: sort
    # TODO: paging

    message = CharField()
    severity = CharField()
    dismissed = CharField()
    created_at = DateTimeField()
    type = CharField()
    subtype = CharField()

    class Meta:
        authentication = CsrfAuthentication()
        authorization = Authorization()
        list_allowed_methods = ['get']
        detail_allowed_methods = []
        fields = ['message', 'severity', 'dismissed', 'created_at']
        resource_name = 'notification'

    def obj_get_list(self, request=None, **kwargs):

        notifications = list([alert.downcast() for alert in AlertState.objects.all()] +
                             [event.downcast() for event in Event.objects.all()] +
                             [command for command in Command.objects.all()])

        return notifications

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

    def dehydrate_message(self, bundle):
        try:
            #  Alerts and Events have a message method
            return bundle.obj.message()
        except TypeError:
            #  Commands have a message attribute
            return bundle.obj.message

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

    def dehydrate_dismissed(self, bundle):
        #  Alerts, Events and Commands all have a dismmissed attribute
        return bundle.obj.dismissed

    def dehydrate_created_at(self, bundle):
        try:
            #  Events and Commands each have a created_at attribute
            return bundle.obj.created_at
        except AttributeError:
            #  Alerts have a begin attribute
            return bundle.obj.begin
