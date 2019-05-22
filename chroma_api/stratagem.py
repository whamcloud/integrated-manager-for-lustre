from django.db import models

from tastypie import fields
from tastypie.resources import Resource
from chroma_api.authentication import AnonymousAuthentication
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from chroma_core.models import StratagemConfiguration

from chroma_api.chroma_model_resource import ChromaModelResource


class StratagemConfigurationValidation(Validation):
    def is_valid(self, bundle, request=None):
        if len(bundle.data.get("objects", [bundle.data])) > 0:
            return {}
        else:
            return {"__all__": "Stratagem configuration not populated."}


class StratagemConfigurationResource(ChromaModelResource):
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

    def obj_create(self, bundle, **kwargs):
        super(StratagemConfigurationResource, self).obj_create(bundle, **kwargs)
        stratagem_data = bundle.data.get("objects", [bundle.data])

        command_id = JobSchedulerClient.configure_stratagem(stratagem_data[0])
