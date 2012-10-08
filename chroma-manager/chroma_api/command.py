#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import custom_response
from chroma_api.host import HostResource

from chroma_core.models import Command
from tastypie.resources import ModelResource
from tastypie import fields, http
from chroma_core.models.jobs import SchedulingError, StepResult
import json


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
            help_text = "Jobs belonging to this command")

    logs = fields.CharField()

    def dehydrate_logs(self, bundle):
        command = bundle.obj
        return "\n".join([stepresult.log for stepresult in StepResult.objects.filter(job__command = command).order_by('modified_at')])

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
        for job in bundle.data['jobs']:
            # FIXME: HYD-1367: This is a hack to work around the inability of
            # the Job class to handle m2m references properly, serializing hosts
            # to a list of IDs understood by the HostListMixin class
            if 'hosts' in job['args']:
                job_ids = []
                for uri in job['args']['hosts']:
                    job_ids.append(HostResource().get_via_uri(uri).id)
                del job['args']['hosts']
                job['args']['host_ids'] = json.dumps(job_ids)

        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
        try:
            command_id = JobSchedulerClient.command_run_jobs(bundle.data['jobs'], bundle.data['message'])
        except SchedulingError, e:
            raise custom_response(self, request, http.HttpBadRequest,
                    {'state': e.message})

        bundle.obj = Command.objects.get(pk = command_id)
        return bundle
