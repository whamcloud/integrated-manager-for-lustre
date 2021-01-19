# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_api.host import ServerProfileResource

from tastypie.authorization import DjangoAuthorization
from tastypie.fields import ToOneField, CharField
from tastypie.validation import Validation
from tastypie.exceptions import Unauthorized

from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import CustomModelResource, DateSerializer
from chroma_core.models import RegistrationToken
from emf_common.lib.date_time import EMFDateTime

import settings


class TokenAuthorization(DjangoAuthorization):
    """
    Only allow filesystem_administrators and higher access to registration tokens
    """

    def read_list(self, object_list, bundle):
        request = bundle.request

        if request.user.groups.filter(name__in=["filesystem_administrators", "superusers"]).exists():
            return object_list
        else:
            return object_list.none()

    def read_detail(self, object_list, bundle):
        request = bundle.request

        if request.user.groups.filter(name__in=["filesystem_administrators", "superusers"]).exists():
            return True
        else:
            raise Unauthorized("You are not allowed to access that resource.")


class RegistrationTokenValidation(Validation):
    """
    Limit which fields are settable during POST and PATCH (because these are
    different sets, setting readonly on the resource fields won't work)
    """

    def is_valid(self, bundle, request=None):
        errors = {}
        if request.method == "POST":
            ALLOWED_CREATION_ATTRIBUTES = ["expiry", "credits", "profile"]
            for attr in bundle.data.keys():
                if attr not in ALLOWED_CREATION_ATTRIBUTES:
                    errors[attr] = ["Forbidden during creation"]
            if not "profile" in bundle.data or not bundle.data["profile"]:
                errors["profile"] = ["Mandatory"]
        elif request.method == "PATCH":
            READONLY_ATTRIBUTES = ["secret", "expiry", "credits"]

            token_id = bundle.data.get("id")

            if not token_id:
                return {"id": "Id field is missing"}

            rt = RegistrationToken.objects.get(id=token_id)

            for attr in bundle.data.keys():
                if attr in READONLY_ATTRIBUTES:
                    if bundle.data[attr] != getattr(rt, attr):
                        errors[attr] = ["May not be modified after creation"]

        return errors


class RegistrationTokenResource(CustomModelResource):
    """
    Server registration tokens.  To add a server via HTTPS registration, acquire
    one of these first.

    POSTs may be passed 'expiry' and 'credits'

    PATCHs may only be passed 'cancelled'
    """

    profile = ToOneField(
        ServerProfileResource,
        "profile",
        null=False,
        help_text="Server profile to be used when setting up servers using this token",
    )

    register_command = CharField(help_text="Command line to run on a storage server to register it using this token")

    def dehydrate_register_command(self, bundle):
        server_profile = ServerProfileResource().get_via_uri(bundle.data["profile"], bundle.request)

        return "curl -k %sagent/setup/%s/%s | python" % (
            settings.SERVER_HTTP_URL,
            bundle.obj.secret,
            "?profile_name=%s" % server_profile.name,
        )

    class Meta:
        object_class = RegistrationToken
        authentication = AnonymousAuthentication()
        authorization = TokenAuthorization()
        serializer = DateSerializer()
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["patch", "get"]
        fields = ["id", "secret", "expiry", "credits", "cancelled", "profile", "register_command"]
        resource_name = "registration_token"
        queryset = RegistrationToken.objects.filter(cancelled=False, expiry__gt=EMFDateTime.utcnow(), credits__gt=0)
        validation = RegistrationTokenValidation()
        always_return_data = True
