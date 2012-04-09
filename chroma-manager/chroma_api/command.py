#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication

from chroma_core.models import Command
from tastypie.resources import ModelResource
from tastypie import fields
from chroma_core.models.utils import await_async_result
from chroma_core.tasks import command_run_jobs


class CommandValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)
        if request.method != 'POST':
            return errors

        mandatory_fields = ['jobs', 'message']
        for f in mandatory_fields:
            if not f in bundle.data or bundle.data[f] is None:
                errors[f].append("This attribute is mandatory")

        if len(errors):
            return errors

        for job in bundle.data['jobs']:
            if not 'class_name' in job:
                errors['jobs'].append("job objects must have the `class_name` attribute")
                continue
            if not 'args' in job:
                errors['jobs'].append("job objects must have the `args` attribute")

            try:
                ContentType.objects.get_by_natural_key('chroma_core', job['class_name'].lower())
            except ContentType.DoesNotExist:
                errors['jobs'].append("Invalid class_name '%s'" % job['class_name'])

        return errors


class CommandResource(ModelResource):
    """
    Commands are created for asynchronous user actions (202 ACCEPTED responses
    contain command objects).  The command resource can be used to query the details
    and state of these asynchronous operations.

    Typically this is used to poll a command for completion and find out whether it
    succeeded.
    """
    jobs = fields.ToManyField("chroma_api.job.JobResource", 'jobs',
            help_text = "Jobs belonging to this command (not populated until \
                    ``jobs_created`` is true")

    class Meta:
        queryset = Command.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']
        ordering = ['created_at']
        filtering = {'complete': ['exact'], 'id': ['exact', 'in']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        validation = CommandValidation()
        always_return_data = True

    def obj_create(self, bundle, request = None):
        async_result = command_run_jobs.delay(bundle.data['jobs'], bundle.data['message'])
        command_id = await_async_result(async_result)
        bundle.obj = Command.objects.get(pk = command_id)
        return bundle
