# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import json

from django.contrib.contenttypes.models import ContentType
from tastypie.resources import Resource
from tastypie.bundle import Bundle
from tastypie import fields
from tastypie.validation import Validation

from chroma_api.step import StepResource
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_core.models import Job, StateLock
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_api.chroma_model_resource import ChromaModelResource
from chroma_api.validation_utils import validate


class StateLockResource(Resource):
    locked_item_id = fields.IntegerField()
    locked_item_content_type_id = fields.IntegerField()
    locked_item_uri = fields.CharField()

    def dehydrate_locked_item_id(self, bundle):
        return bundle.obj.locked_item.id

    def dehydrate_locked_item_content_type_id(self, bundle):
        locked_item = bundle.obj.locked_item
        if hasattr(locked_item, "content_type"):
            return locked_item.content_type.id
        else:
            return ContentType.objects.get_for_model(locked_item).id

    def dehydrate_locked_item_uri(self, bundle):
        from chroma_api.urls import api

        locked_item = bundle.obj.locked_item
        if hasattr(locked_item, "content_type"):
            locked_item = locked_item.downcast()

        return api.get_resource_uri(locked_item)

    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs["pk"] = bundle_or_obj.obj.locked_item.id
        else:
            kwargs["pk"] = bundle_or_obj.locked_item.id

        return kwargs

    class Meta:
        object_class = StateLock
        resource_name = "state_lock"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()


class JobValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = {}
        try:
            job = Job.objects.get(pk=bundle.data["id"]).downcast()
        except KeyError:
            errors["id"] = "Attribute mandatory"
        except Job.DoesNotExist:
            errors["id"] = "Job with id %s not found" % bundle.data["id"]
        else:
            try:
                new_state = bundle.data["state"]
            except KeyError:
                errors["state"] = "Attribute mandatory"
            else:
                valid_states = ["cancelled", job.state]
                if not new_state in valid_states:
                    errors["state"] = "Must be one of %s" % valid_states

        return errors


class JobResource(ChromaModelResource):
    """
    Jobs refer to individual units of work that the server is doing.  Jobs
    may either run as part of a Command, or on their own.  Jobs which are necessary
    to the completion of more than one command may belong to more than one command.

    For example:

    * a Command to start a filesystem has a Job for starting each OST.
    * a Command to setup an OST has a series of Jobs for formatting, registering etc

    Jobs which are part of the same command may run in parallel to one another.

    The lock objects in the ``read_locks`` and ``write_locks`` fields have the
    following form:

    ::

        {
            id: "1",
            locked_item_id: 2,
            locked_item_content_type_id: 4,
        }

    The ``id`` and ``content_type_id`` of the locked object form a unique identifier
    which can be compared with API-readable objects which have such attributes.
    """

    description = fields.CharField(
        help_text="Human readable string around\
            one sentence long describing what the job is doing"
    )
    wait_for = fields.ListField(
        "wait_for", null=True, help_text="List of other jobs which must complete before this job can run"
    )
    read_locks = fields.ListField(
        null=True,
        help_text="List of objects which must stay in the required state while\
            this job runs",
    )
    write_locks = fields.ListField(
        null=True,
        help_text="List of objects which must be in a certain state for\
            this job to run, and may be modified by this job while it runs.",
    )
    commands = fields.ToManyField(
        "chroma_api.command.CommandResource",
        lambda bundle: bundle.obj.command_set.all(),
        null=True,
        help_text="Commands which require this job to complete\
            sucessfully in order to succeed themselves",
    )
    steps = fields.ToManyField(
        "chroma_api.step.StepResource",
        lambda bundle: bundle.obj.stepresult_set.all(),
        null=True,
        help_text="Steps executed within this job",
    )
    step_results = fields.DictField(help_text="List of step results")
    class_name = fields.CharField(help_text="Internal class name of job")

    available_transitions = fields.DictField()

    def _dehydrate_locks(self, bundle, write):
        if bundle.obj.locks_json:
            locks = json.loads(bundle.obj.locks_json)
            locks = [StateLock.from_dict(bundle.obj, lock) for lock in locks if lock["write"] == write]
            slr = StateLockResource()
            return [slr.full_dehydrate(slr.build_bundle(obj=l)).data for l in locks]
        else:
            return []

    def dehydrate_wait_for(self, bundle):
        if not bundle.obj.wait_for_json:
            return []
        else:
            wait_fors = json.loads(bundle.obj.wait_for_json)
            return [JobResource().get_resource_uri(Job.objects.get(pk=i)) for i in wait_fors]

    def dehydrate_read_locks(self, bundle):
        return self._dehydrate_locks(bundle, write=False)

    def dehydrate_write_locks(self, bundle):
        return self._dehydrate_locks(bundle, write=True)

    def dehydrate_class_name(self, bundle):
        return bundle.obj.content_type.model_class().__name__

    def dehydrate_available_transitions(self, bundle):
        job = bundle.obj.downcast()
        if job.state == "complete" or not job.cancellable:
            return []
        elif job.cancellable:
            return [{"state": "cancelled", "label": "Cancel"}]

    def dehydrate_step_results(self, bundle):
        result = {}

        for step_result in bundle.obj.stepresult_set.all():
            result[StepResource().get_resource_uri(step_result)] = (
                json.loads(step_result.result) if step_result.result else None
            )
        return result

    def dehydrate_description(self, bundle):
        return bundle.obj.downcast().description()

    class Meta:
        queryset = Job.objects.all()
        resource_name = "job"
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ["task_id", "locks_json", "wait_for_json"]
        ordering = ["created_at"]
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get", "put"]
        filtering = {"id": ["exact", "in"], "state": ["exact", "in"]}
        always_return_data = True
        validation = JobValidation()

    @validate
    def obj_update(self, bundle, **kwargs):
        job = Job.objects.get(pk=kwargs["pk"])
        new_state = bundle.data["state"]

        if new_state == "cancelled":
            JobSchedulerClient.cancel_job(job.pk)
            Job.objects.get(pk=kwargs["pk"])

        bundle.obj = job
        return bundle
