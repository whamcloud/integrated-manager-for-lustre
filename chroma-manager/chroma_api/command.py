#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import json
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from tastypie.validation import Validation
from tastypie.utils import trailing_slash
from tastypie.api import url
from tastypie.resources import ModelResource
from tastypie import fields, http

from chroma_api.authentication import AnonymousAuthentication
from chroma_api.authentication import PATCHSupportDjangoAuth
from chroma_api.utils import custom_response
from chroma_api.host import HostResource

from chroma_core.models import Command
from chroma_core.models.jobs import SchedulingError, StepResult
from long_polling_api import LongPollingAPI


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


class CommandResource(ModelResource, LongPollingAPI):
    """
    Asynchronous user-initiated operations which create, remove or modify resources are
    represented by ``command`` objects.  When a PUT, POST, PATCH or DELETE to
    a resource returns a 202 ACCEPTED response, the response body contains
    a command identifier.  The ``command`` resource is used to query the status
    of these asynchronous operations.

    Typically this is used to poll a command for completion and find out whether it
    succeeded.
    """
    jobs = fields.ToManyField("chroma_api.job.JobResource", 'jobs',
                              help_text = "Jobs belonging to this command")

    logs = fields.CharField(help_text = "String.  Concatentation of all user-visible logs from the"
                            "``job`` objects associated with this command.")

    # Long polling should return when any of the tables below changes or has changed.
    long_polling_tables = [Command]

    def dispatch(self, request_type, request, **kwargs):
        return self.handle_long_polling_dispatch(request_type, request, **kwargs)

    def dehydrate_logs(self, bundle):
        command = bundle.obj
        return "\n".join([stepresult.log for stepresult in StepResult.objects.filter(job__command = command).order_by('modified_at')])

    class Meta:
        queryset = Command.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'patch']
        ordering = ['created_at']
        filtering = {'complete': ['exact'],
                     'id': ['exact', 'in'],
                     'dismissed': ['exact'],
                     'errored': ['exact'],
                     'created_at': ['gte', 'lte', 'gt', 'lt'],
                     'cancelled': ['exact']}
        authorization = PATCHSupportDjangoAuth()
        authentication = AnonymousAuthentication()
        validation = CommandValidation()
        always_return_data = True

    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/dismiss_all%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('dismiss_all'), name='api_command_dismiss_all'),
        ]

    def dismiss_all(self, request, **kwargs):
        if (request.method != 'PUT') or (not request.user.is_authenticated()):
            return http.HttpUnauthorized()

        Command.objects.filter(dismissed = False, complete = True).update(dismissed = True)

        return http.HttpNoContent()

    def obj_create(self, bundle, request = None, **kwargs):
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
