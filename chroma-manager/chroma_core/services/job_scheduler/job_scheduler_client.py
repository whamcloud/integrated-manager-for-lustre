#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.job import job_log
from chroma_core.lib.util import all_subclasses
from chroma_core.services.job_scheduler.lock_cache import LockCache
from chroma_core.services.rpc import ServiceRpcInterface
from django.contrib.contenttypes.models import ContentType


class JobSchedulerRpcInterface(ServiceRpcInterface):
    methods = ['set_state', 'notify_state', 'run_jobs', 'cancel_job']


class JobSchedulerClient(object):
    """Expose the job_scheduler service's functionality to the rest of Chroma: some of
    these calls are implemented as RPCs, and some run in the calling process.

    """
    @classmethod
    def command_run_jobs(cls, job_dicts, message):
        return JobSchedulerRpcInterface().run_jobs(job_dicts, message)

    @classmethod
    def command_set_state(cls, object_ids, message, run = True):
        return JobSchedulerRpcInterface().set_state(object_ids, message, run)

    @classmethod
    def notify_state(cls, instance, time, new_state, from_states):
        """from_states: list of states it's valid to transition from.  This lets
           the audit code safely update the state of e.g. a mount it doesn't find
           to 'unmounted' without risking incorrectly transitioning from 'unconfigured'"""
        if instance.state in from_states and instance.state != new_state:
            job_log.info("Enqueuing notify_state %s %s->%s at %s" % (instance, instance.state, new_state, time))
            time_serialized = time.isoformat()
            return JobSchedulerRpcInterface().notify_state(instance.content_type.natural_key(), instance.id, time_serialized, new_state, from_states)

    @classmethod
    def available_transitions(cls, stateful_object):
        """Return a list states to which the object can be set from
           its current state, or None if the object is currently
           locked by a Job"""
        if hasattr(stateful_object, 'content_type'):
            stateful_object = stateful_object.downcast()

        # We don't advertise transitions for anything which is currently
        # locked by an incomplete job.  We could alternatively advertise
        # which jobs would actually be legal to add by skipping this check and
        # using get_expected_state in place of .state below.
        if LockCache().get_latest_write(stateful_object):
            return []

        # XXX: could alternatively use expected_state here if you want to advertise
        # what jobs can really be added (i.e. advertise transitions which will
        # be available when current jobs are complete)
        #from_state = self.get_expected_state(stateful_object)
        from_state = stateful_object.state
        available_states = stateful_object.get_available_states(from_state)
        transitions = []
        for to_state in available_states:
            try:
                verb = stateful_object.get_verb(from_state, to_state)
            except KeyError:
                job_log.warning("Object %s in state %s advertised an unreachable state %s" % (stateful_object, from_state, to_state))
            else:
                # NB: a None verb means its an internal transition that shouldn't be advertised
                if verb:
                    transitions.append({"state": to_state, "verb": verb})

        return transitions

    @classmethod
    def available_jobs(cls, instance):
        # If the object is subject to an incomplete Job
        # then don't offer any actions
        if LockCache().get_latest_write(instance) > 0:
            return []

        from chroma_core.models import AdvertisedJob

        available_jobs = []
        for aj in all_subclasses(AdvertisedJob):
            if not aj.plural:
                for class_name in aj.classes:
                    ct = ContentType.objects.get_by_natural_key('chroma_core', class_name)
                    klass = ct.model_class()
                    if isinstance(instance, klass):
                        if aj.can_run(instance):
                            available_jobs.append({
                                'verb': aj.verb,
                                'confirmation': aj.get_confirmation(instance),
                                'class_name': aj.__name__,
                                'args': aj.get_args(instance)})

        return available_jobs

    @classmethod
    def get_transition_consequences(cls, stateful_object, new_state):
        from chroma_core.services.job_scheduler.state_manager import ModificationOperation

        # FIXME: deps calls use a global instance of ObjectCache, calling them from outside
        # the JobScheduler service is a problem -- get rid of the singletons and pass refs around.
        ObjectCache.clear()
        return ModificationOperation(LockCache()).get_transition_consequences(stateful_object, new_state)

    @classmethod
    def cancel_job(cls, job_id):
        JobSchedulerRpcInterface().cancel_job(job_id)
