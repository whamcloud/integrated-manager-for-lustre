#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


import httpagentparser

from tastypie.resources import Resource
from tastypie.authorization import Authorization

from chroma_api.authentication import CsrfAuthentication
from chroma_core.services.log import custom_log_register

logger = custom_log_register(__name__, 'client_errors.log')


class ClientErrorResource(Resource):
    """
    A JavaScript Client Error.

    Designed for POST only.  Each POST will write a block to the
    client_errors.log log file.

    GET is not supported; this resource cannot be queried.
    """

    class Meta:
        authentication = CsrfAuthentication()
        authorization = Authorization()
        resource_name = 'client_error'
        list_allowed_methods = ['post']
        detail_allowed_methods = []
        always_return_data = False
        object_class = dict  # Not used, but required

    def get_resource_uri(self, bundle):
        return None  # not used, but required

    def obj_create(self, bundle, request=None, **kwargs):

        url = bundle.data.get('url', None)
        message = bundle.data.get('message', None)
        stack = bundle.data.get('stack', None)
        user_agent = bundle.request.META.get('HTTP_USER_AGENT', '')
        os, browser = httpagentparser.simple_detect(user_agent)

        logger.error("%s, url: %s, os: %s, browser: %s" % (message, url, os, browser))
        logger.error("user agent: %s" % user_agent)
        for line in stack.split("\n"):
            logger.error(line)
        logger.error("")

        return bundle
