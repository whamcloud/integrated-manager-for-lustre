#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import Command
from tastypie.resources import ModelResource
from tastypie import fields


class CommandResource(ModelResource):
    jobs = fields.ToManyField("chroma_api.job.JobResource", 'jobs')

    class Meta:
        queryset = Command.objects.all()
