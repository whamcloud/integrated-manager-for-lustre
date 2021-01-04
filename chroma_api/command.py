# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import json
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from tastypie.validation import Validation
from tastypie.utils import trailing_slash
from tastypie.api import url
from tastypie import fields, http

from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_api.utils import custom_response
from chroma_api.host import HostResource
from chroma_api.chroma_model_resource import ChromaModelResource

from chroma_core.models import Command
from chroma_core.models.jobs import SchedulingError
from chroma_core.models import StepResult
from chroma_api.validation_utils import validate


class CommandValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)
        if request.method != "POST":
            return errors

        mandatory_fields = ["jobs", "message"]
        for f in mandatory_fields:
            if not f in bundle.data or bundle.data[f] is None:
                errors[f].append("This attribute is mandatory")

        if len(errors):
            return errors

        for job in bundle.data["jobs"]:
            if not "class_name" in job:
                errors["jobs"].append("job objects must have the `class_name` attribute")
                continue
            if not "args" in job:
                errors["jobs"].append("job objects must have the `args` attribute")

            try:
                ContentType.objects.get_by_natural_key("chroma_core", job["class_name"].lower())
            except ContentType.DoesNotExist:
                errors["jobs"].append("Invalid class_name '%s'" % job["class_name"])

        return errors


class CommandResource(ChromaModelResource):
    """
    Asynchronous user-initiated operations which create, remove or modify resources are
    represented by ``command`` objects.  When a PUT, POST, PATCH or DELETE to
    a resource returns a 202 ACCEPTED response, the response body contains
    a command identifier.  The ``command`` resource is used to query the status
    of these asynchronous operations.

    Typically this is used to poll a command for completion and find out whether it
    succeeded.
    """

    jobs = fields.ToManyField("chroma_api.job.JobResource", "jobs", help_text="Jobs belonging to this command")

    logs = fields.CharField(
        help_text="String.  Concatentation of all user-visible logs from the"
        "``job`` objects associated with this command."
    )

    def dehydrate_logs(self, bundle):
        command = bundle.obj
        return "\n".join(
            [stepresult.log for stepresult in StepResult.objects.filter(job__command=command).order_by("modified_at")]
        )

    class Meta:
        queryset = Command.objects.all()
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "patch"]
        ordering = ["created_at"]
        filtering = {
            "complete": ["exact"],
            "id": ["exact", "in"],
            "dismissed": ["exact"],
            "errored": ["exact"],
            "created_at": ["gte", "lte", "gt", "lt"],
            "cancelled": ["exact"],
        }
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        validation = CommandValidation()
        always_return_data = True

    def prepend_urls(self):
        return [
            url(
                r"^(?P<resource_name>%s)/dismiss_all%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("dismiss_all"),
                name="api_command_dismiss_all",
            )
        ]

    def dismiss_all(self, request, **kwargs):
        if (request.method != "PUT") or (not request.user.is_authenticated()):
            return http.HttpUnauthorized()

        Command.objects.filter(dismissed=False, complete=True).update(dismissed=True)

        return http.HttpNoContent()

    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request

        for job in bundle.data["jobs"]:
            # FIXME: HYD-1367: This is a hack to work around the inability of
            # the Job class to handle m2m references properly, serializing hosts
            # to a list of IDs understood by the HostListMixin class
            if "hosts" in job["args"]:
                job_ids = []
                for uri in job["args"]["hosts"]:
                    job_ids.append(HostResource().get_via_uri(uri, bundle.request).id)
                del job["args"]["hosts"]
                job["args"]["host_ids"] = json.dumps(job_ids)

        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

        try:
            command_id = JobSchedulerClient.command_run_jobs(bundle.data["jobs"], bundle.data["message"])
        except SchedulingError as e:
            raise custom_response(self, request, http.HttpBadRequest, {"state": e.message})

        bundle.obj = Command.objects.get(pk=command_id)
        return bundle
