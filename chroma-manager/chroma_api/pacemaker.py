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
from chroma_core.models import PacemakerConfiguration
from chroma_core.services import log_register
from chroma_api.utils import StatefulModelResource
from chroma_api.utils import BulkResourceOperation
from chroma_api.authentication import AnonymousAuthentication

log = log_register(__name__)


###
# Allows read and update of LNetConfiguration
#
# Responds to
#
# Get
# https://localhost:8000/api/corosync_configuration/1/
# https://localhost:8000/api/corosync_configuration/
#
# Put
# https://localhost:8000/api/corosync_configuration/
# https://localhost:8000/api/corosync_configuration/1/
class PacemakerConfigurationResource(StatefulModelResource, BulkResourceOperation):
    """
    LNetConfiguration information.
    """
    host = fields.ToOneField('chroma_api.host.HostResource', 'host', full=False)

    # Long polling should return when any of the tables below changes or has changed.
    long_polling_tables = [ManagedHost, PacemakerConfiguration]

    class Meta:
        queryset = PacemakerConfiguration.objects.all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = 'pacemaker_configuration'
        list_allowed_methods = ['get', 'put']
        detail_allowed_methods = ['get', 'put']
        filtering = {'host': ALL_WITH_RELATIONS,
                     'id': ['exact'],
                     'host__fqdn': ['exact', 'startswith']}
