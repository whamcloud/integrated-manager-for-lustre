from django.db import models

from tastypie import fields
from tastypie.resources import Resource
from chroma_api.authentication import AnonymousAuthentication
from tastypie.authorization import DjangoAuthorization
from chroma_core.models import Stratagem

from chroma_api.chroma_model_resource import ChromaModelResource


class StratagemResource(ChromaModelResource):
    interval = fields.IntegerField(attribute="interval")
    report_duration = fields.IntegerField(attribute="report_duration")
    report_duration_active = fields.BooleanField(attribute="report_duration_active")
    purge_duration = fields.IntegerField(attribute="purge_duration")
    purge_duration_active = fields.BooleanField(attribute="purge_duration_active")

    class Meta:
        resource_name = "stratagem"
        queryset = Stratagem.objects.all()
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        allowed_methods = ["get", "post"]

