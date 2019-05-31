from django.db import models

from tastypie import fields
from tastypie.resources import Resource
from chroma_api.authentication import AnonymousAuthentication
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from chroma_api.validation_utils import validate
from chroma_core.models import StratagemConfiguration, ManagedHost, ManagedMdt, ManagedTargetMount, ManagedFilesystem

from chroma_api.chroma_model_resource import ChromaModelResource


class RunStratagemValidation(Validation):
    def is_valid(self, bundle, request=None):
        if "filesystem_id" not in bundle.data:
            return {"__all__": "filesystem_id required when running stratagem."}
        else:
            filesystem_id = bundle.data.get("filesystem_id")

            try:
                ManagedFilesystem.objects.get(id=filesystem_id)
            except ManagedFilesystem.DoesNotExist:
                return {"__all__": "Filesystem {} does not exist.".format(bundle.data.get("filesystem_id"))}

            # Each MDT associated with the fielsystem must be installed on a server that has the stratagem profile installed
            target_mount_ids = map(
                lambda mdt: mdt.active_mount_id,
                ManagedMdt.objects.filter(filesystem_id=bundle.data.get("filesystem_id")),
            )
            host_ids = map(
                lambda target_mount: target_mount.host_id, ManagedTargetMount.objects.filter(id__in=target_mount_ids)
            )
            installed_profiles = map(lambda host: host.server_profile_id, ManagedHost.objects.filter(id__in=host_ids))
            if all(map(lambda name: name == "stratagem_server", installed_profiles)):
                return {}
            else:
                return {"__all__": "'stratagem_servers' profile must be installed on all MDT servers."}


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

        if len(difference) == 0:
            return super(StratagemConfigurationValidation, self).is_valid(bundle, request)
        else:
            return {"__all__": "Required fields are missing: {}".format(", ".join(difference))}


class StratagemConfigurationResource(ChromaModelResource):
    filesystem_id = fields.IntegerField(attribute="filesystem_id", null=False)
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
    filesystem_id = fields.IntegerField(attribute="filesystem_id", null=False)

    class Meta:
        list_allowed_methods = ["post"]
        detail_allowed_methods = []
        resource_name = "run_stratagem"
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        object_class = dict
        validation = RunStratagemValidation()

    @validate
    def obj_create(self, bundle, **kwargs):
        mdts = map(lambda mdt: mdt.id, ManagedMdt.objects.filter(filesystem_id=bundle.data.get("filesystem_id")))
        return JobSchedulerClient.run_stratagem(mdts)
