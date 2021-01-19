# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from collections import defaultdict

from tastypie.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist
import tastypie.http as http
from tastypie import fields
from tastypie.constants import ALL_WITH_RELATIONS

from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services import log_register
from chroma_api.utils import dehydrate_command
from chroma_api.utils import custom_response
from chroma_api.network_interface import NetworkInterfaceResource
from chroma_api.lnet_configuration import LNetConfigurationResource
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_core.models import Command
from chroma_core.models import Nid
from chroma_api.validation_utils import ChromaValidation, validate
from chroma_api.chroma_model_resource import ChromaModelResource

log = log_register(__name__)


class NidValidation(ChromaValidation):
    mandatory_message = "This field is mandatory"

    def is_valid(self, bundle, request=None, **kwargs):
        errors = defaultdict(list)

        if request.method != "POST":
            return errors

        for nids_data in bundle.data.get("objects", [bundle.data]):
            if "lnd_network" not in nids_data:
                errors["lnd_network"] = ["Field lnd_network not present in data"]

            if not errors:
                self.validate_object(
                    nids_data,
                    errors,
                    {
                        "lnd_network": self.Expectation(True),
                        "network_interface": self.Expectation(True),
                        "lnd_type": self.Expectation(int(nids_data["lnd_network"] != -1)),
                        "resource_uri": self.Expectation(False),
                        "lnet_configuration": self.Expectation(False),
                    },
                )

            if not errors:
                self.validate_resources(
                    [
                        self.URIInfo(nids_data.get("lnet_configuration", None), LNetConfigurationResource),
                        self.URIInfo(nids_data["network_interface"], NetworkInterfaceResource),
                    ],
                    errors,
                    request,
                )

            if not errors:
                # Check the lnd_type passed is valid for the network_interface
                if ("lnd_type" in nids_data) and (
                    nids_data["lnd_type"]
                    not in NetworkInterfaceResource().get_via_uri(nids_data["network_interface"], request).lnd_types
                ):
                    errors["lnd_type"].append(
                        "lnd_type %s not valid for interface %s"
                        % (
                            nids_data["lnd_type"],
                            NetworkInterfaceResource().get_via_uri(nids_data["network_interface"], request),
                        )
                    )

        return errors


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
class NidResource(ChromaModelResource):
    """
    Nid information.
    """

    network_interface = fields.ToOneField("chroma_api.network_interface.NetworkInterfaceResource", "network_interface")
    lnet_configuration = fields.ToOneField(
        "chroma_api.lnet_configuration.LNetConfigurationResource", "lnet_configuration"
    )

    class Meta:
        queryset = Nid.objects.select_related("network_interface", "lnet_configuration").all()

        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        validation = NidValidation()
        resource_name = "nid"
        list_allowed_methods = ["get", "post", "delete"]
        detail_allowed_methods = ["get", "post", "put", "delete"]
        filtering = {"network_interface": ALL_WITH_RELATIONS, "lnet_configuration": ALL_WITH_RELATIONS, "id": ["exact"]}

    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        if "objects" in bundle.data:
            nids_data = bundle.data["objects"]
        else:
            nids_data = [bundle.data]

        for nid_data in nids_data:
            nid_data["network_interface"] = (
                NetworkInterfaceResource().get_via_uri(nid_data["network_interface"], bundle.request).id
            )

        command_id = JobSchedulerClient.update_nids(nids_data)

        try:
            command = Command.objects.get(pk=command_id)
        except ObjectDoesNotExist:
            command = None

        raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})

    @validate
    def obj_update(self, bundle, **kwargs):
        self.obj_create(bundle, **kwargs)

    def obj_delete_list(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete_list``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        try:
            obj_list = self.obj_get_list(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        self._nids_delete(obj_list)

    def obj_delete(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        try:
            obj = self.obj_get(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        self._nids_delete([obj])

    def _nids_delete(self, obj_list):
        delete_list = []

        for nid in obj_list:
            delete_list.append({"network_interface": nid.network_interface_id, "lnd_network": -1})

        if len(delete_list) > 0:
            JobSchedulerClient.update_nids(delete_list)
