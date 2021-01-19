# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from tastypie import fields
from tastypie.constants import ALL_WITH_RELATIONS

from chroma_core.models import NetworkInterface
from chroma_core.services import log_register
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.chroma_model_resource import ChromaModelResource

log = log_register(__name__)


###
# Allows read NetworkInterfaces
#
# Responds to
#
# Get
# https://localhost:8000/api/network_interface/1/
# https://localhost:8000/api/network_interface/   - filter by host_id
#
class NetworkInterfaceResource(ChromaModelResource):
    """
    NetworkInterface information.
    """

    host = fields.ToOneField("chroma_api.host.HostResource", "host", full=False)
    nid = fields.ToOneField("chroma_api.nid.NidResource", "nid", full=True, null=True)
    lnd_types = fields.ListField()

    class Meta:
        queryset = NetworkInterface.objects.select_related("host", "nid").all()
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = "network_interface"
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get"]
        filtering = {"host": ALL_WITH_RELATIONS, "id": ["exact"]}

    def dehydrate_lnd_types(self, bundle):
        return bundle.obj.lnd_types
