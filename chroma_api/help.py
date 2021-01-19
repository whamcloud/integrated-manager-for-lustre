# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import chroma_core.lib.conf_param
from chroma_core.models import ManagedOst, ManagedMdt
from chroma_core.models.filesystem import ManagedFilesystem

from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization

from tastypie.http import HttpBadRequest
from tastypie.resources import Resource


class HelpResource(Resource):
    """
    This resource provides contextual help for use in user interfaces.

    GETs to the ``/conf_param/`` sub-url respond with help for Lustre configuration
    parameters.  There are two ways to do this GET:

    * Set the ``keys`` parameter to a comma-separated list of configuration parameter
      names to get help for particular parameters.
    * Set the ``kind`` parameter to one of 'OST', 'MDT' or 'FS' to get all possible
      configuration parameters for this type of object.

    The response is a dictionary where the key is a configuration parameter name
    and the value is a help string.
    """

    class Meta:
        object_class = dict
        resource_name = "help"
        detail_allowed_methods = []
        list_allowed_methods = []
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()

    def prepend_urls(self):
        from django.conf.urls import url

        return [
            url(
                r"^(?P<resource_name>%s)/conf_param/$" % self._meta.resource_name,
                self.wrap_view("conf_param_help"),
                name="api_conf_param_help",
            )
        ]

    def conf_param_help(self, request, **kwargs):
        """
        One of 'kind' or 'keys' must be set

        :param keys: comma separated list of strings
        :param kind: one of 'OST', 'MDT' or 'FS'"""
        kind = request.GET.get("kind", None)
        keys = request.GET.get("keys", None)

        if kind:
            klass = {"OST": ManagedOst, "MDT": ManagedMdt, "FS": ManagedFilesystem}[kind]

            return self.create_response(request, chroma_core.lib.conf_param.get_possible_conf_params(klass))
        elif keys:
            keys = keys.split(",")
            return self.create_response(
                request, dict([(key, chroma_core.lib.conf_param.get_conf_param_help(key)) for key in keys])
            )
        else:
            return self.create_response(request, {"kind": ["This field is mandatory"]}, response_class=HttpBadRequest)
