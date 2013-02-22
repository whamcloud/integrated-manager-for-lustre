#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.models.jobs import StepResult
from tastypie.resources import ModelResource
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from tastypie import fields


class StepResource(ModelResource):
    """
    A step belongs to a Job.  Steps execute sequentially, and may be retried.
    A given Job may have multiple 'step 1' records if retries have occurred, in which
    case they may be distinguished by their ``created_at`` attributes.

    The details of the steps for a job are usually only interesting if something has gone wrong
    and the user is interested in any captured exceptions or console output.

    Don't load steps for a job unless they're really needed; the console output may be
    large.
    """
    class Meta:
        queryset = StepResult.objects.all()
        resource_name = 'step'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['step_klass']
        filtering = {'job': ['exact'], 'id': ['exact', 'in']}
        ordering = ['created_at', 'modified_at']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']

    description = fields.CharField()

    def dehydrate_description(self, bundle):
        return bundle.obj.describe()

    class_name = fields.CharField(help_text = "Name of the class representing this step")

    def dehydrate_class_name(self, bundle):
        return bundle.obj.step_klass_name()

    args = fields.DictField()

    def dehydrate_args(self, bundle):
        return bundle.obj.args
