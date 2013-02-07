#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.services import log_register

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
    timeout = None

    def __init__(self, job, args, result):
        self.args = args
        self.job_id = job.id

        # A StepResult object
        self.result = result

        # This step is the final one in the job
        self.final = False

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

    def run(self, kwargs):
        raise NotImplementedError

    def log(self, message):
        job_log.info("Job %s %s: %s" % (self.job_id, self.__class__.__name__, message))
        self.result.log += "%s\n" % message
        self.result.save()

    def _log_subprocesses(self, subprocesses):
        for subprocess in subprocesses:
            self.result.console += "%s: %s\n%s\n%s\n" % (" ".join(subprocess['args']), subprocess['rc'], subprocess['stdout'], subprocess['stderr'])
            self.result.save()

    def invoke_agent(self, host, command, args = {}):
        """
        Wrapper around AgentRpc.call which stashes console output in self.result
        """
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc, AgentException

        job_log.info("invoke_agent on agent %s %s %s" % (host, command, args))

        try:
            result, action_state = AgentRpc.call(host.fqdn, command, args)
            self._log_subprocesses(action_state.subprocesses)
            return result
        except AgentException as e:
            self._log_subprocesses(e.subprocesses)
            raise


class IdempotentStep(Step):
    idempotent = True


class AnyTargetMountStep(Step):
    def _run_agent_command(self, target, command, args):
        # There is a set of hosts that we can try to contact to start the target: assume
        # that anything with a TargetMount on is part of the corosync cluster and can be
        # used to issue a command to start this resource.

        # Try and use each targetmount, the one with the most recent successful audit first
        from chroma_core.models import ManagedTargetMount
        # FIXME: HYD-1238: use an authentic online/offline state to select where to run
        available_tms = ManagedTargetMount.objects.filter(target = target)
        if available_tms.count() == 0:
            raise RuntimeError("No hosts are available for target %s" % target)
        available_tms = list(available_tms)

        for tm in available_tms:
            job_log.debug("command '%s' on target %s trying targetmount %s" % (command, target, tm))

            try:
                return self.invoke_agent(tm.host, command, args)
                # Success!
            except Exception:
                job_log.warning("Cannot run '%s' on %s." % (command, tm.host))
                if tm == available_tms[-1]:
                    job_log.error("No targetmounts of target %s could run '%s'." % (target, command))
                    # Re-raise the exception if there are no further TMs to try on
                    raise

        # Should never fall through, if succeeded then returned, if failed all then
        # re-raise exception on last failure
        assert False
