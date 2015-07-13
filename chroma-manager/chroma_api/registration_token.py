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


import datetime
from chroma_api.host import ServerProfileResource
import dateutil

from tastypie.authorization import DjangoAuthorization
from tastypie.fields import ToOneField, CharField
from tastypie.validation import Validation

from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import CustomModelResource
from chroma_core.models import RegistrationToken

import settings


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
            ALLOWED_CREATION_ATTRIBUTES = ['expiry', 'credits', 'profile']
            for attr in bundle.data.keys():
                if attr not in ALLOWED_CREATION_ATTRIBUTES:
                    errors[attr] = ["Forbidden during creation"]
            if not 'profile' in bundle.data or not bundle.data['profile']:
                errors['profile'] = ["Mandatory"]
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

    profile = ToOneField(ServerProfileResource, 'profile', null=False,
                         help_text="Server profile to be used when setting up servers using this token")

    register_command = CharField(help_text="Command line to run on a storage server to register it using this token")

    def dehydrate_register_command(self, bundle):
        server_profile = ServerProfileResource().get_via_uri(bundle.data['profile'])

        return 'curl -k %sagent/setup/%s/%s | python' % (settings.SERVER_HTTP_URL, bundle.obj.secret, '?profile_name=%s' % server_profile.name)

    class Meta:
        object_class = RegistrationToken
        authentication = AnonymousAuthentication()
        authorization = TokenAuthorization()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['patch', 'get']
        fields = ['id', 'secret', 'expiry', 'credits', 'cancelled', 'profile', 'register_command']
        resource_name = 'registration_token'
        queryset = RegistrationToken.objects.filter(
            cancelled = False,
            expiry__gt = datetime.datetime.now(dateutil.tz.tzutc()),
            credits__gt = 0)
        validation = RegistrationTokenValidation()
        always_return_data = True
