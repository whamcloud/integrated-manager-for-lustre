# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from tastypie import fields
from tastypie.constants import ALL_WITH_RELATIONS

from chroma_core.models.pacemaker import PacemakerConfiguration
from chroma_core.services import log_register
from chroma_api.utils import StatefulModelResource
from chroma_api.utils import BulkResourceOperation
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
class PacemakerConfigurationResource(StatefulModelResource, BulkResourceOperation):
    """
    LNetConfiguration information.
    """

    host = fields.ToOneField("chroma_api.host.HostResource", "host", full=False)

    class Meta:
        queryset = PacemakerConfiguration.objects.all()
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        resource_name = "pacemaker_configuration"
        list_allowed_methods = ["get", "put"]
        detail_allowed_methods = ["get", "put"]
        filtering = {"host": ALL_WITH_RELATIONS, "id": ["exact"], "host__fqdn": ["exact", "startswith"]}
