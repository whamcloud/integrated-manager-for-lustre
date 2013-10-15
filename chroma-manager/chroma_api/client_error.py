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


from tastypie.resources import ModelResource
from tastypie.authorization import Authorization

from chroma_api.authentication import CsrfAuthentication

from chroma_core.models import ClientError


class ClientErrorResource(ModelResource):
    """
    A Client Error.

    """
    class Meta:
        authentication = CsrfAuthentication()
        authorization = Authorization()
        queryset = ClientError.objects.all()
        resource_name = 'client_error'
        excludes = ['browser', 'created_at']
        list_allowed_methods = ['post']
        detail_allowed_methods = []

    def hydrate_user_agent(self, bundle):
        bundle.data['user_agent'] = bundle.request.META.get('HTTP_USER_AGENT', '')

        return bundle
