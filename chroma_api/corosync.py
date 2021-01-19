# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from tastypie import fields
from tastypie.constants import ALL_WITH_RELATIONS
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from django.urls import resolve


from chroma_core.models import CorosyncConfiguration
from chroma_core.services import log_register
from chroma_api.utils import StatefulModelResource
from chroma_api.utils import BulkResourceOperation
from chroma_api.utils import dehydrate_command
from chroma_api.validation_utils import validate
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization

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
class CorosyncConfigurationResource(StatefulModelResource, BulkResourceOperation):
    """
    LNetConfiguration information.
    """

    host = fields.ToOneField("chroma_api.host.HostResource", "host", full=False)

    network_interfaces = fields.ListField(
        null=True, help_text="Network interfaces the form part of the corosync configuration."
    )

    class Meta:
        queryset = CorosyncConfiguration.objects.all()
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = "corosync_configuration"
        list_allowed_methods = ["get", "put"]
        detail_allowed_methods = ["get", "put"]
        filtering = {"host": ALL_WITH_RELATIONS, "id": ["exact"], "host__fqdn": ["exact", "startswith"]}

    @validate
    def obj_update(self, bundle, **kwargs):
        request = bundle.request
        super(CorosyncConfigurationResource, self).obj_update(bundle, **kwargs)

        def _update_corosync_configuration(self, corosync_configuration, request, **kwargs):
            network_interface_ids = [
                resolve(interwork_interface)[2]["pk"]
                for interwork_interface in corosync_configuration["network_interfaces"]
            ]

            return self.BulkActionResult(
                dehydrate_command(
                    JobSchedulerClient.update_corosync_configuration(
                        corosync_configuration_id=corosync_configuration["id"],
                        mcast_port=corosync_configuration["mcast_port"],
                        network_interface_ids=network_interface_ids,
                    )
                ),
                None,
                None,
            )

        self._bulk_operation(_update_corosync_configuration, "command", bundle, request, **kwargs)

    def dehydrate_network_interfaces(self, bundle):
        from chroma_api.urls import api

        return [api.get_resource_uri(network_interface) for network_interface in bundle.obj.network_interfaces]
