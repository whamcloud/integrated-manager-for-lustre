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


from chroma_core.models import NetworkInterface, Nid, LNetConfiguration
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services import log_register
from chroma_api.utils import custom_response, dehydrate_command
from chroma_core.models import Command
from tastypie.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist

from tastypie.resources import ModelResource

import tastypie.http as http
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from tastypie.constants import ALL_WITH_RELATIONS

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
class LNetConfigurationResource(ModelResource):
    """
    LNetConfiguration information.
    """
    host = fields.ToOneField('chroma_api.host.HostResource', 'host', full=True)
    nids = fields.ToManyField('chroma_api.network_interface.NidResource', 'nid_set', full=True, null=True)

    class Meta:
        queryset = LNetConfiguration.objects.all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = 'lnet_configuration'
        list_allowed_methods = ['get', 'put']
        detail_allowed_methods = ['get', 'put']
        filtering = {'host': ALL_WITH_RELATIONS,
                     'id': ['exact']}

    def obj_update(self, bundle, request = None, **kwargs):
        if 'objects' in bundle.data:
            lnet_configurations_data = bundle.data['objects']
        else:
            lnet_configurations_data = [bundle.data]

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


###
# Allows read and update of Nid
#
# Responds to
#
# Get
# https://localhost:8000/api/nid/1/
# https://localhost:8000/api/nid/
#
# Put
# https://localhost:8000/api/nid/1
#
# Post
# https://localhost:8000/api/nid/
#
# Delete
# https://localhost:8000/api/nid/1/
# https://localhost:8000/api/nid/
class NidResource(ModelResource):
    """
    Nid information.
    """
    network_interface = fields.ToOneField('chroma_api.network_interface.NetworkInterfaceResource', 'network_interface')
    lnet_configuration = fields.ToOneField('chroma_api.network_interface.LNetConfigurationResource', 'lnet_configuration')

    class Meta:
        queryset = Nid.objects.select_related('network_interface', 'lnet_configuration').all()

        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = 'nid'
        list_allowed_methods = ['get', 'post', 'delete']
        detail_allowed_methods = ['get', 'post', 'put', 'delete']
        filtering = {'network_interface': ALL_WITH_RELATIONS,
                     'lnet_configuration': ALL_WITH_RELATIONS,
                     'id': ['exact']}

    def obj_create(self, bundle, request = None, **kwargs):
        if 'objects' in bundle.data:
            nids_data = bundle.data['objects']
        else:
            nids_data = [bundle.data]

        for nid_data in nids_data:
            nid_data['network_interface'] = NetworkInterfaceResource().get_via_uri(nid_data['network_interface']).id

        host_id, command_id = JobSchedulerClient.update_nids(nids_data)

        try:
            command = Command.objects.get(pk = command_id)
        except ObjectDoesNotExist:
            command = None

        raise custom_response(self, request, http.HttpAccepted,
                              {
                                  'command': dehydrate_command(command)
                              })

    def obj_update(self, bundle, request = None, **kwargs):
        self.obj_create(bundle, request, **kwargs)

    def obj_delete_list(self, request, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete_list``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        try:
            obj_list = self.obj_get_list(request, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        self._nids_delete(obj_list)

    def obj_delete(self, request=None, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        try:
            obj = self.obj_get(request, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        self._nids_delete([obj])

    def _nids_delete(self, obj_list):
        delete_list = []

        for nid in obj_list:
            delete_list.append({'network_interface': nid.network_interface_id, 'lnd_network': -1})

        if (len(delete_list) > 0):
            JobSchedulerClient.update_nids(delete_list)


###
# Allows read NetworkInterfaces
#
# Responds to
#
# Get
# https://localhost:8000/api/network_interface/1/
# https://localhost:8000/api/network_interface/   - filter by host_id
#
class NetworkInterfaceResource(ModelResource):
    """
    NetworkInterface information.
    """
    host = fields.ToOneField('chroma_api.host.HostResource', 'host', full=True)
    nid = fields.ToOneField('chroma_api.network_interface.NidResource', 'nid', full=True, null=True)

    class Meta:
        queryset = NetworkInterface.objects.select_related('host', 'nid').all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = 'network_interface'
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        filtering = {'host': ALL_WITH_RELATIONS,
                     'id': ['exact']}
