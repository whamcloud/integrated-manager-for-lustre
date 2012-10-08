#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""
The service `job_scheduler` handles both RPCs (JobSchedulerRpc) and a queue (NotificationQueue).
The RPCs are used for explicit requests to modify the system or run a particular task, while the queue
is used for updates received from agent reports.  Access to both of these, along with some additional
non-remote functionality is wrapped in JobSchedulerClient.

"""

from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.job import job_log
from chroma_core.lib.util import all_subclasses
from chroma_core.services.job_scheduler.lock_cache import LockCache
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface
from django.contrib.contenttypes.models import ContentType


class NotificationQueue(ServiceQueue):
    name = 'job_scheduler_notifications'


class JobSchedulerRpc(ServiceRpcInterface):
    methods = ['set_state', 'run_jobs', 'cancel_job']


class JobSchedulerClient(object):
    """Because there are some tasks which are the domain of the job scheduler but do not need to
    be run in the context of the service, the RPCs and queue operations are accompanied in this
    class by some operations that run locally.  The local operations are
    read-only operations such as querying what operations are possible for a particular object.

    """
    @classmethod
    def command_run_jobs(cls, job_dicts, message):
        """Create and run some Jobs, within a single Command.

        :param job_dicts: List of 1 or more dicts like {'class_name': 'MyJobClass', 'args': {<dict of arguments to Job constructor>}}
        :param message: User-visible string describing the operation, e.g. "Detecting filesystems"
        :return: The ID of a new Command

        """
        return JobSchedulerRpc().run_jobs(job_dicts, message)

    @classmethod
    def command_set_state(cls, object_ids, message, run = True):
        """Modify the system in whatever way is necessary to reach the state
        specified in `object_ids`.  Creates Jobs under a single Command.  May create
        no Jobs if the system is already in the state, or already scheduled to be
        in that state.  If the system is already scheduled to be in that state, then
        the returned Command will be connected to the existing Jobs which take the system to
        the desired state.

        :param cls:
        :param object_ids: List of three-tuples (natural_key, object_id, new_state)
        :param message: User-visible string describing the operation, e.g. "Starting filesystem X"
        :param run: Test only.  Schedule jobs without starting them.
        :return: The ID of a new Command

        """
        return JobSchedulerRpc().set_state(object_ids, message, run)

    @classmethod
    def notify_state(cls, instance, time, new_state, from_states):
        """Having detected that the state of an object in the database does not
        match information from real life (i.e. chroma-agent), call this to
        request an update to the object.

        :param instance: An instance of a StatefulObject
        :param time: A UTC datetime.datetime object
        :param new_state: The new value of the `state` attribute
        :param from_states: A list of states from which the instance may be
                            set to the new state.  This lets updates happen
                            safely without risking e.g. notifying an 'unconfigured'
                            LNet state to 'lnet_down'.

        :return: None

        """

        if instance.state in from_states and instance.state != new_state:
            job_log.info("Enqueuing notify_state %s %s->%s at %s" % (instance, instance.state, new_state, time))
            time_serialized = time.isoformat()
            NotificationQueue().put({
                'instance_natural_key': instance.content_type.natural_key(),
                'instance_id': instance.id,
                'time': time_serialized,
                'new_state': new_state,
                'from_states': from_states
            })

    @classmethod
    def available_transitions(cls, stateful_object):
        """Query which new states can be set for an object, depending on its
        current state.  Provides a list of states and descriptive verbs for
        use in presentation.  Note that the verb for a particular state is
        not always the same, for example transitioning to 'lnet_down' could
        either be "Load LNet module" or "Stop LNet" depending on whether the
        object is in lnet_unloaded or lnet_up.

        :param stateful_object: Instance of a StatefulObject
        :return: A list of dicts like {'state': '<new state>', 'verb': '<human readable verb>'}
        """
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
        """Query which jobs (other than changes to state) can be run on this object.

        :param instance: Instance of a StatefulObject
        :return: A list of dicts like {'verb': '<Human readable description>', 'confirmation': '<Human readable confirmation prompt or None', 'class_name': '<Job class name>', 'args': {<dict of args to job constructor}}
        """
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
        """Query what the side effects of a state transition are.  Effectively does
        a dry run of scheduling jobs for the transition.

        The return format is like this:
        ::

            {
                'transition_job': <job dict>,
                'dependency_jobs': [<list of job dicts>]
            }
            # where each job dict is like
            {
                'class': '<job class name>',
                'requires_confirmation': <boolean, whether to prompt for confirmation>,
                'confirmation_prompt': <string, confirmation prompt>,
                'description': <string, description of the job>,
                'stateful_object_id': <ID of the object modified by this job>,
                'stateful_object_content_type_id': <Content type ID of the object modified by this job>
            }

        :param stateful_object: A StatefulObject instance
        :param new_state: Hypothetical new value of the 'state' attribute

        """
        from chroma_core.services.job_scheduler.command_plan import CommandPlan

        # FIXME: deps calls use a global instance of ObjectCache, calling them from outside
        # the JobScheduler service is a problem -- get rid of the singletons and pass refs around.
        ObjectCache.clear()
        return CommandPlan(LockCache()).get_transition_consequences(stateful_object, new_state)

    @classmethod
    def cancel_job(cls, job_id):
        """Attempt to cancel a job which is already scheduled (and possibly running)

        :param job_id: ID of a Job object
        """
        JobSchedulerRpc().cancel_job(job_id)
