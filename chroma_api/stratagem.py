from django.db import models
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from toolz.functoolz import pipe, partial, flip, compose

import tastypie.http as http

from tastypie import fields
from tastypie.resources import Resource
from chroma_api.authentication import AnonymousAuthentication
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from chroma_api.validation_utils import validate
from chroma_api.utils import custom_response, dehydrate_command
from chroma_core.models import (
    StratagemConfiguration,
    ManagedHost,
    ManagedMdt,
    ManagedTargetMount,
    ManagedFilesystem,
    Command,
    get_fs_id_from_identifier,
)

from chroma_api.chroma_model_resource import ChromaModelResource

get_bundle_int_val = compose(partial(flip, int, 10), str)


class RunStratagemValidation(Validation):
    def is_valid(self, bundle, request=None):
        try:
            purge_duration = bundle.data.get("purge_duration") and get_bundle_int_val(bundle.data.get("purge_duration"))
        except ValueError:
            return {"code": "invalid_argument", "message": "Purge duration must be an integer value."}

        try:
            report_duration = bundle.data.get("report_duration") and get_bundle_int_val(
                bundle.data.get("report_duration")
            )
        except ValueError:
            return {"code": "invalid_argument", "message": "Report duration must be an integer value."}

        if "filesystem" not in bundle.data:
            return {"code": "filesystem_required", "message": "Filesystem required."}
        elif purge_duration and report_duration and report_duration >= purge_duration:
            return {"code": "duration_order_error", "message": "Report duration must be less than purge duration."}

        fs_identifier = str(bundle.data.get("filesystem"))
        fs_id = get_fs_id_from_identifier(fs_identifier)
        if not fs_id:
            return {
                "code": "filesystem_does_not_exist",
                "message": "Filesystem {} does not exist.".format(fs_identifier),
            }

        # Each MDT associated with the fielsystem must be installed on a server that has the stratagem profile installed
        target_mount_ids = map(lambda mdt: mdt.active_mount_id, ManagedMdt.objects.filter(filesystem_id=fs_id))
        host_ids = map(
            lambda target_mount: target_mount.host_id, ManagedTargetMount.objects.filter(id__in=target_mount_ids)
        )
        host_ids = pipe(host_ids, set, list)
        installed_profiles = map(lambda host: host.server_profile_id, ManagedHost.objects.filter(id__in=host_ids))
        if not all(map(lambda name: name == "stratagem_server", installed_profiles)):
            return {
                "code": "stratagem_server_profile_not_installed",
                "message": "'stratagem_servers' profile must be installed on all MDT servers.",
            }

        return {}


class StratagemConfigurationValidation(RunStratagemValidation):
    def is_valid(self, bundle, request=None):
        required_args = [
            "interval",
            "report_duration",
            "report_duration_active",
            "purge_duration",
            "purge_duration_active",
        ]

        difference = set(required_args) - set(bundle.data.keys())

        if not difference:
            return super(StratagemConfigurationValidation, self).is_valid(bundle, request)

        return {"__all__": "Required fields are missing: {}".format(", ".join(difference))}


class StratagemConfigurationResource(ChromaModelResource):
    filesystem = fields.CharField(attribute="filesystem_id", null=False)
    interval = fields.IntegerField(attribute="interval", null=False)
    report_duration = fields.IntegerField(attribute="report_duration", null=False)
    report_duration_active = fields.BooleanField(attribute="report_duration_active", null=False)
    purge_duration = fields.IntegerField(attribute="purge_duration", null=False)
    purge_duration_active = fields.BooleanField(attribute="purge_duration_active", null=False)

    class Meta:
        resource_name = "stratagem_configuration"
        queryset = StratagemConfiguration.objects.all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        allowed_methods = ["get", "post"]
        validation = StratagemConfigurationValidation()

    @validate
    def obj_create(self, bundle, **kwargs):
        return JobSchedulerClient.configure_stratagem(bundle.data)


class RunStratagemResource(Resource):
    filesystem = fields.CharField(attribute="filesystem_id", null=False)
    report_duration = fields.IntegerField(attribute="report_duration", null=True)
    purge_duration = fields.IntegerField(attribute="purge_duration", null=True)

    class Meta:
        list_allowed_methods = ["post"]
        detail_allowed_methods = []
        resource_name = "run_stratagem"
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        object_class = dict
        validation = RunStratagemValidation()

    def get_resource_uri(self, bundle=None, url_name=None):
        return Resource.get_resource_uri(self)

    @validate
    def obj_create(self, bundle, **kwargs):
        fs_identifier = str(bundle.data.get("filesystem"))
        fs_id = get_fs_id_from_identifier(fs_identifier)

        mdts = map(lambda mdt: mdt.id, ManagedMdt.objects.filter(filesystem_id=fs_id))

        command_id = JobSchedulerClient.run_stratagem(mdts, bundle.data)

        try:
            command = Command.objects.get(pk=command_id)
        except ObjectDoesNotExist:
            command = None

        raise custom_response(self, bundle.request, http.HttpAccepted, {"command": dehydrate_command(command)})
