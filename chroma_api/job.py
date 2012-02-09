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
    class Meta:
        queryset = StateLock.objects.all()
        resource_name = 'state_lock'
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()


class JobResource(ModelResource):
    description = fields.CharField()
    wait_for = fields.ToManyField('chroma_api.job.JobResource', 'wait_for', null = True)
    read_locks = fields.ToManyField(StateLockResource,
            lambda bundle: StateReadLock.objects.filter(job = bundle.obj), full = True, null = True)
    write_locks = fields.ToManyField(StateLockResource,
            lambda bundle: StateWriteLock.objects.filter(job = bundle.obj), full = True, null = True)
    #command = fields.ToManyField('chroma_api.command.CommandResource',
    #        lambda bundle: bundle.obj.commands.all(), full = True, null = True)

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
        excludes = ['wait_for_completions', 'wait_for_count']

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
