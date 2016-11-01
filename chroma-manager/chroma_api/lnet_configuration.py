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

from django.core.exceptions import ObjectDoesNotExist
import tastypie.http as http
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.constants import ALL_WITH_RELATIONS

from chroma_core.models import LNetConfiguration
from chroma_core.models import ManagedHost
from chroma_core.models import Nid
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services import log_register
from chroma_api.utils import dehydrate_command
from chroma_api.utils import custom_response, StatefulModelResource
from chroma_api.authentication import AnonymousAuthentication
from chroma_core.models import Command

log = log_register(__name__)


###
# Allows read and update of LNetConfiguration
#
# Responds to
#
# Get
# https://localhost:8000/api/lnet_configuration/1/
# https://localhost:8000/api/lnet_configuration/
#
# Put
# https://localhost:8000/api/lnet_configuration/
# https://localhost:8000/api/lnet_configuration/1/
class LNetConfigurationResource(StatefulModelResource):
    """
    LNetConfiguration information.
    """
    host = fields.ToOneField('chroma_api.host.HostResource', 'host', full=True)     # full to support the cli
    nids = fields.ToManyField('chroma_api.nid.NidResource', 'nid_set', full=False, null=True)

    class Meta:
        queryset = LNetConfiguration.objects.all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = 'lnet_configuration'
        list_allowed_methods = ['get', 'put']
        detail_allowed_methods = ['get', 'put']
        filtering = {'host': ALL_WITH_RELATIONS,
                     'id': ['exact'],
                     'host__fqdn': ['exact', 'startswith']}

    # Long polling should return when any of the tables below changes or has changed.
    long_polling_tables = [LNetConfiguration, ManagedHost, Nid]

    def obj_update(self, bundle, request = None, **kwargs):
        if 'pk' in kwargs:
            return super(LNetConfigurationResource, self).obj_update(bundle, request, **kwargs)

        lnet_configurations_data = bundle.data.get('objects', [bundle.data])

        lnet_configuration = []

        for lnet_configuration_data in lnet_configurations_data:
            lnet_configuration.append({"host_id": lnet_configuration_data['host']['id'],
                                       "state": lnet_configuration_data['state']})

        command_id = JobSchedulerClient.update_lnet_configuration(lnet_configuration)

        try:
            command = Command.objects.get(pk = command_id)
        except ObjectDoesNotExist:
            command = None

        raise custom_response(self, request, http.HttpAccepted,
                              {
                                  'command': dehydrate_command(command)
                              })
