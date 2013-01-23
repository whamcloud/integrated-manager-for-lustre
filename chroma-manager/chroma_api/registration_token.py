#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
import dateutil

from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation

from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import CustomModelResource
from chroma_core.models import RegistrationToken


class TokenAuthorization(DjangoAuthorization):
    """
    Only allow filesystem_administrators and higher access to registration tokens
    """
    def apply_limits(self, request, object_list):
        if request.user.groups.filter(name__in = ['filesystem_administrators', 'superusers']).exists():
            return object_list
        else:
            return object_list.none()


class RegistrationTokenValidation(Validation):
    """
    Limit which fields are settable during POST and PATCH (because these are
    different sets, setting readonly on the resource fields won't work)
    """
    def is_valid(self, bundle, request = None):
        errors = {}
        if request.method == 'POST':
            ALLOWED_CREATION_ATTRIBUTES = ['expiry', 'credits']
            for attr in bundle.data.keys():
                if attr not in ALLOWED_CREATION_ATTRIBUTES:
                    errors[attr] = ["Forbidden during creation"]
        elif request.method == "PATCH":
            READONLY_ATTRIBUTES = ['secret', 'expiry', 'credits']
            for attr in bundle.data.keys():
                if attr in READONLY_ATTRIBUTES:
                    if bundle.data[attr] != getattr(bundle.obj, attr):
                        errors[attr] = ["May not be modified after creation"]

        return errors


class RegistrationTokenResource(CustomModelResource):
    """
    Server registration tokens.  To add a server via HTTPS registration, acquire
    one of these first.

    POSTs may be passed 'expiry' and 'credits'

    PATCHs may only be passed 'cancelled'
    """

    class Meta:
        object_class = RegistrationToken
        authentication = AnonymousAuthentication()
        authorization = TokenAuthorization()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['patch', 'get']
        fields = ['id', 'secret', 'expiry', 'credits', 'cancelled']
        resource_name = 'registration_token'
        queryset = RegistrationToken.objects.filter(
            cancelled = False,
            expiry__gt = datetime.datetime.now(dateutil.tz.tzutc()),
            credits__gt = 0)
        validation = RegistrationTokenValidation()
