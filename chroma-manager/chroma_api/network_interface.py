#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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
from tastypie.authorization import DjangoAuthorization
from tastypie.constants import ALL_WITH_RELATIONS

from chroma_core.models import ManagedHost
from chroma_core.models import NetworkInterface
from chroma_core.services import log_register
from chroma_api.authentication import AnonymousAuthentication
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
    host = fields.ToOneField('chroma_api.host.HostResource', 'host', full=False)
    nid = fields.ToOneField('chroma_api.nid.NidResource', 'nid', full=True, null=True)
    lnd_types = fields.ListField()

    # Long polling should return when any of the tables below changes or has changed.
    long_polling_tables = [ManagedHost, NetworkInterface]

    class Meta:
        queryset = NetworkInterface.objects.select_related('host', 'nid').all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = 'network_interface'
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        filtering = {'host': ALL_WITH_RELATIONS,
                     'id': ['exact']}

    def dehydrate_lnd_types(self, bundle):
        return bundle.obj.lnd_types
