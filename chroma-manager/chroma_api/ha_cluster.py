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


from tastypie import fields
from tastypie.resources import Resource
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.host import HostResource
from chroma_core.models import HaCluster


class HaClusterResource(Resource):
    peers = fields.ListField(attribute = 'peers')

    def dehydrate_peers(self, bundle):
        hr = HostResource()
        return [hr.full_dehydrate(hr.build_bundle(p)) for p in bundle.obj.peers]

    def get_object_list(self, request):
        return HaCluster.all_clusters()

    def obj_get_list(self, request=None, **kwargs):
        return self.get_object_list(request)

    class Meta:
        resource_name = 'ha_cluster'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ['get']
        detail_allowed_methods = []
        include_resource_uri = False
