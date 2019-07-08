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
        elif purge_duration is not None and report_duration is not None and report_duration >= purge_duration:
            return {"code": "duration_order_error", "message": "Report time must be less than purge time."}

        fs_identifier = str(bundle.data.get("filesystem"))
        fs_id = get_fs_id_from_identifier(fs_identifier)
        if fs_id is None:
            return {
                "code": "filesystem_does_not_exist",
                "message": "Filesystem {} does not exist.".format(fs_identifier),
            }
        elif ManagedFilesystem.objects.get(id=fs_id).state != "available":
            return {"code": "filesystem_unavailable", "message": "Filesystem {} is unavailable.".format(fs_identifier)}

        # At least Mdt 0 should be mounted, or stratagem cannot run.
        target_mount_ids = (
            ManagedMdt.objects.filter(filesystem_id=fs_id, active_mount_id__isnull=False)
            .values_list("active_mount_id", flat=True)
            .distinct()
        )
        mdt0 = ManagedMdt.objects.filter(filesystem_id=fs_id, name__contains="MDT0000").first()

        if mdt0 is None:
            return {"code": "mdt0_not_found", "message": "MDT0 could not be found."}

        if mdt0.active_mount_id not in target_mount_ids:
            return {"code": "mdt0_not_mounted", "message": "MDT0 must be mounted in order to run stratagem."}

        host_ids = (
            ManagedTargetMount.objects.filter(id__in=target_mount_ids).values_list("host_id", flat=True).distinct()
        )

        installed_profiles = (
            ManagedHost.objects.filter(id__in=host_ids).values_list("server_profile_id", flat=True).distinct()
        )

        if not all(map(lambda name: name == "stratagem_server", installed_profiles)):
            return {
                "code": "stratagem_server_profile_not_installed",
                "message": "'stratagem_servers' profile must be installed on all MDT servers.",
            }

        if not ManagedHost.objects.filter(server_profile_id="stratagem_client").exists():
            return {
                "code": "stratagem_client_profile_not_installed",
                "message": "A client must be added with the 'Stratagem Client' profile to run this command.",
            }

        return {}


class StratagemConfigurationValidation(RunStratagemValidation):
    def is_valid(self, bundle, request=None):
        required_args = ["interval", "filesystem"]

        difference = set(required_args) - set(bundle.data.keys())

        if not difference:
            return super(StratagemConfigurationValidation, self).is_valid(bundle, request)

        return {"__all__": "Required fields are missing: {}".format(", ".join(difference))}


class StratagemConfigurationResource(ChromaModelResource):
    filesystem = fields.CharField(attribute="filesystem_id", null=False)
    interval = fields.IntegerField(attribute="interval", null=False)
    report_duration = fields.IntegerField(attribute="report_duration", null=True)
    purge_duration = fields.IntegerField(attribute="purge_duration", null=True)

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
        fs_identifier = bundle.data.get("filesystem")
        fs_id = get_fs_id_from_identifier(fs_identifier)

        mdts = list(
            ManagedMdt.objects.filter(filesystem_id=fs_id, active_mount_id__isnull=False).values_list("id", flat=True)
        )

        command_id = JobSchedulerClient.run_stratagem(mdts, bundle.data)

        try:
            command = Command.objects.get(pk=command_id)
        except ObjectDoesNotExist:
            command = None

        raise custom_response(self, bundle.request, http.HttpAccepted, {"command": dehydrate_command(command)})
