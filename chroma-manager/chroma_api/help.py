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


import chroma_core.lib.conf_param
from chroma_core.models import ManagedOst, ManagedMdt, ManagedFilesystem

from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication

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
        resource_name = 'help'
        detail_allowed_methods = []
        list_allowed_methods = []
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()

    def override_urls(self):
        from django.conf.urls import url
        return [
            url(r"^(?P<resource_name>%s)/conf_param/$" % self._meta.resource_name, self.wrap_view('conf_param_help'), name="api_conf_param_help"),
        ]

    def conf_param_help(self, request, **kwargs):
        """
         One of 'kind' or 'keys' must be set

         :param keys: comma separated list of strings
         :param kind: one of 'OST', 'MDT' or 'FS'"""
        kind = request.GET.get('kind', None)
        keys = request.GET.get('keys', None)

        if kind:
            klass = {
                    "OST": ManagedOst,
                    "MDT": ManagedMdt,
                    "FS": ManagedFilesystem
                    }[kind]

            return self.create_response(request, chroma_core.lib.conf_param.get_possible_conf_params(klass))
        elif keys:
            keys = keys.split(",")
            return self.create_response(request, dict([(key, chroma_core.lib.conf_param.get_conf_param_help(key)) for key in keys]))
        else:
            return self.create_response(request, {'kind': ["This field is mandatory"]}, response_class = HttpBadRequest)
