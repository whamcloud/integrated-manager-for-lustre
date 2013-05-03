#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


from chroma_core.services import log_register
import django.db.models

job_log = log_register('job')


class Dependable(object):
    def all(self):
        if hasattr(self, 'objects'):
            for o in self.objects:
                for i in o.all():
                    yield i
        else:
            yield self

    def debug_list(self):
        if hasattr(self, 'objects'):
            result = []
            for o in self.objects:
                result.append((o.__class__.__name__, o.debug_list()))
            return result
        else:
            return [self.stateful_object, self.acceptable_states]

    def satisfied(self):
        """Return True or False for whether this and all child
           dependencies are satisfied (i.e. their required state
           is set on their object)"""
        return NotImplementedError


class DependOn(Dependable):
    def __init__(self,
            stateful_object,
            preferred_state,
            acceptable_states = None,
            fix_state = None):
        """preferred_state: what we will try to put the dependency into if
           it is not already in one of acceptable_states.
           fix_state: what we will try to put the depender into if his
           dependency can no longer be satisfied."""

        assert isinstance(stateful_object, django.db.models.Model)

        if not acceptable_states:
            self.acceptable_states = [preferred_state]
        else:
            if not preferred_state in acceptable_states:
                self.acceptable_states = acceptable_states + [preferred_state]
            else:
                self.acceptable_states = acceptable_states

        # Preferred state is a piece of metadata which tells callers how to
        # get our stateful_object into an acceptable state -- i.e. "If X is not
        # in one of Y then put it into Z" where X is stateful_object, Y is
        # acceptable_states, Z is preferred_state.
        self.preferred_state = preferred_state

        # fix_state is a piece of metadata which tells callers how to eliminate
        # this dependency, i.e. "I depend on X in Y but I wouldn't if I was in
        # state Z" where X is stateful_object, Y is acceptable_states, Z is
        # fix_state.
        self.fix_state = fix_state
        self.stateful_object = stateful_object

    def __str__(self):
        return "%s %s %s %s" % (self.stateful_object, self.preferred_state, self.acceptable_states, self.fix_state)

    def get_stateful_object(self):
        return self.stateful_object.__class__._base_manager.get(pk = self.stateful_object.pk)

    def satisfied(self):
        depended_object = self.get_stateful_object()
        satisfied = depended_object.state in self.acceptable_states
        if not satisfied:
            job_log.warning("DependOn not satisfied: %s in state %s, not one of %s (preferred %s)" %
                    (depended_object, depended_object.state, self.acceptable_states, self.preferred_state))
        return satisfied


class MultiDependable(Dependable):
    def __init__(self, *args):
        from collections import Iterable
        if len(args) == 1 and isinstance(args[0], Iterable):
            self.objects = args[0]
        else:
            self.objects = args


class DependAll(MultiDependable):
    """Stores a list of Dependables, all of which must be in the
       desired state for this dependency to be true"""
    def satisfied(self):
        for o in self.objects:
            if not o.satisfied():
                return False

        return True


class DependAny(MultiDependable):
    """Stores a list of Dependables, one or more of which must be in the
       desired state for this dependency to be true"""
    def satisfied(self):
        if len(self.objects) == 0:
            return True

        for o in self.objects:
            if o.satisfied():
                return True

        return False


class Step(object):
    def __init__(self, job, args, log_callback, console_callback, cancel_event):
        self.args = args
        self.job_id = job.id

        self._log_callback = log_callback
        self._console_callback = console_callback

        # This step is the final one in the job
        self.final = False

        self._cancel_event = cancel_event

    @classmethod
    def describe(cls, kwargs):
        return "%s: %s" % (cls.__name__, kwargs)

    def mark_final(self):
        self.final = True

    # Indicate whether the step is idempotent.  For example, mounting
    # a target.  Step subclasses which are always idempotent should set the
    # idempotent class attribute.   Subclasses which may be idempotent should
    # override this attribute.
    idempotent = False

    # If true, this step may use the database (limits concurrency to number of
    # database connections)
    database = False

    def run(self, kwargs):
        raise NotImplementedError

    def log(self, message):
        job_log.info("Job %s %s: %s" % (self.job_id, self.__class__.__name__, message))
        self._log_callback("%s\n" % message)

    def _log_subprocesses(self, subprocesses):
        for subprocess in subprocesses:
            self._console_callback("%s: %s\n%s\n%s\n" % (" ".join(subprocess['args']), subprocess['rc'], subprocess['stdout'], subprocess['stderr']))

    def invoke_agent(self, host, command, args = {}):
        """
        Wrapper around AgentRpc.call which provides logging
        """
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc, AgentException

        job_log.info("invoke_agent on agent %s %s %s" % (host, command, args))

        try:
            result, action_state = AgentRpc.call(host.fqdn, command, args, self._cancel_event)
            self._log_subprocesses(action_state.subprocesses)
            return result
        except AgentException as e:
            self._log_subprocesses(e.subprocesses)
            raise


class IdempotentStep(Step):
    idempotent = True
