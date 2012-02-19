#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication

from chroma_core.models import Job, StateLock, StateReadLock, StateWriteLock


class StateLockResource(ModelResource):
    locked_item_id = fields.IntegerField()
    locked_item_content_type_id = fields.IntegerField()
    locked_item_uri = fields.CharField()

    def dehydrate_locked_item_id(self, bundle):
        return bundle.obj.locked_item_id

    def dehydrate_locked_item_content_type_id(self, bundle):
        locked_item = bundle.obj.locked_item
        if hasattr(locked_item, 'content_type'):
            return locked_item.content_type.id
        else:
            return bundle.obj.locked_item_type.id

    def dehydrate_locked_item_uri(self, bundle):
        from chroma_api.urls import api
        locked_item = bundle.obj.locked_item
        if hasattr(locked_item, 'content_type'):
            locked_item = locked_item.downcast()

        return api.get_resource_uri(locked_item)

    class Meta:
        queryset = StateLock.objects.all()
        resource_name = 'state_lock'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()


class JobResource(ModelResource):
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

    The ``id`` and ``content_type_id`` of the locked object form a unique identify
    which can be compared with API-readable objects which have such attributes.
    """

    description = fields.CharField(help_text = "Human readable string around\
            one sentence long describing what the job is doing")
    wait_for = fields.ToManyField('chroma_api.job.JobResource', 'wait_for', null = True,
            help_text = "List of other jobs which must complete before this job can run")
    read_locks = fields.ToManyField(StateLockResource,
            lambda bundle: StateReadLock.objects.filter(job = bundle.obj), full = True, null = True,
            help_text = "List of objects which must stay in the required state while\
            this job runs")
    write_locks = fields.ToManyField(StateLockResource,
            lambda bundle: StateWriteLock.objects.filter(job = bundle.obj), full = True, null = True,
            help_text = "List of objects which must be in a certain state for\
            this job to run, and may be modified by this job while it runs.")
    commands = fields.ToManyField('chroma_api.command.CommandResource',
            lambda bundle: bundle.obj.command_set.all(), null = True,
            help_text = "Commands which require this job to complete\
            sucessfully in order to succeed themselves")

    available_transitions = fields.DictField()

    def dehydrate_available_transitions(self, bundle):
        job = bundle.obj
        if job.state in ['complete', 'completing', 'cancelling']:
            return []
        elif job.state == 'paused':
            return [{'state': 'resume', 'label': "Resume"}]
        elif job.state in ['pending', 'tasked']:
            return [{'state': 'pause', 'label': 'Pause'},
                    {'state': 'cancel', 'label': 'Cancel'}]
        else:
            raise NotImplementedError

    def dehydrate_description(self, bundle):
        return bundle.obj.description()

    class Meta:
        queryset = Job.objects.all()
        resource_name = 'job'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        excludes = ['wait_for_completions', 'wait_for_count', 'finished_step', 'started_step', 'task_id']
        ordering = ['created_at']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'put']
        filtering = {'id': ['exact', 'in']}

    def obj_update(self, bundle, request, **kwargs):
        """Modify a Job (setting 'state' field to 'pause', 'cancel', or 'resume' is the
        only allowed input e.g. {'state': 'pause'}"""
        # FIXME: 'cancel' and 'resume' aren't actually a state that job will ever have,
        # it causes a paused job to bounce back into a state like 'pending' or 'tasked'
        # - there should be a better way of representing this operation
        new_state = bundle.data['state']

        assert new_state in ['pause', 'cancel', 'resume']
        if new_state == 'pause':
            bundle.obj.pause()
        elif new_state == 'cancel':
            bundle.obj.cancel()
        else:
            bundle.obj.resume()
        return bundle
