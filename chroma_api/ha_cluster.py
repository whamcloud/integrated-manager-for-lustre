# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from tastypie import fields
from tastypie.resources import Resource
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.host import HostResource
from chroma_core.models import HaCluster


class HaClusterResource(Resource):
    peers = fields.ListField(attribute="peers")

    def dehydrate_peers(self, bundle):
        hr = HostResource()
        return [hr.full_dehydrate(hr.build_bundle(p)) for p in bundle.obj.peers]

    def get_object_list(self, request):
        return HaCluster.all_clusters()

    def obj_get_list(self, bundle, **kwargs):
        return self.get_object_list(bundle.request)

    class Meta:
        resource_name = "ha_cluster"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ["get"]
        detail_allowed_methods = []
        include_resource_uri = False
