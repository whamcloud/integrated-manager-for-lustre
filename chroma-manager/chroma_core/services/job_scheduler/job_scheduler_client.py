#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.job import job_log
from chroma_core.services.rpc import ServiceRpcInterface


class JobSchedulerRpcInterface(ServiceRpcInterface):
    methods = ['set_state', 'notify_state', 'run_jobs']


class JobSchedulerClient(object):
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
        from chroma_core.lib.state_manager import StateManager

        return StateManager().available_transitions(stateful_object)

    @classmethod
    def available_jobs(cls, stateful_object):
        from chroma_core.lib.state_manager import StateManager

        return StateManager().available_jobs(stateful_object)

    @classmethod
    def get_transition_consequences(cls, stateful_object, new_state):
        from chroma_core.lib.state_manager import StateManager

        return StateManager().get_transition_consequences(stateful_object, new_state)
