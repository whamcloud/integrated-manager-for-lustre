from django.db import models

from tastypie import fields
from tastypie.resources import Resource
from chroma_api.authentication import AnonymousAuthentication
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tastypie.authorization import DjangoAuthorization
from chroma_core.models import Stratagem

from chroma_api.chroma_model_resource import ChromaModelResource


class StratagemResource(ChromaModelResource):
    interval = fields.IntegerField(attribute="interval", null=False)
    report_duration = fields.IntegerField(attribute="report_duration", null=False)
    report_duration_active = fields.BooleanField(attribute="report_duration_active", null=False)
    purge_duration = fields.IntegerField(attribute="purge_duration", null=False)
    purge_duration_active = fields.BooleanField(attribute="purge_duration_active", null=False)

    class Meta:
        resource_name = "stratagem"
        queryset = Stratagem.objects.all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        allowed_methods = ["get", "post"]

    def obj_create(self, bundle, **kwargs):
        stratagem_data = bundle.data.get("objects", [bundle.data])
        if len(stratagem_data) > 0:
            command_id = JobSchedulerClient.configure_stratagem(stratagem_data[0])
