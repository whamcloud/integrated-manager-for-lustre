
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings
job_log = settings.setup_log('job')


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
            job_log.warning("DependOn not satisfied: %s in state %s, not one of %s" %
                    (depended_object,
                     depended_object.state,
                     self.acceptable_states))
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

    idempotent = False

    def is_idempotent(self):
        """Indicate whether the step is idempotent.  For example, mounting
           a target.  Step subclasses which are always idempotent should set the
           idempotent class attribute.   Subclasses which may be idempotent should
           override this method."""
        return self.idempotent

    def run(self, kwargs):
        raise NotImplementedError

    def retry(self):
        pass
        # TODO
        #steps = self.get_steps()
        # Which one failed?

    def invoke_agent(self, host, command, args = None):
        def console_callback(chunk):
            self.result.console = self.result.console + chunk
            self.result.save()

        from configure.lib.agent import Agent
        agent = Agent(host = host, log = job_log, console_callback = console_callback)
        return agent.invoke(command, args)


class IdempotentStep(Step):
    idempotent = True


class StateChangeJob(object):
    """Subclasses must define a class attribute 'stateful_object'
       identifying another attribute which returns a StatefulObject"""

    # Tuple of (StatefulObjectSubclass, old_state, new_state)
    state_transition = None
    # Name of an attribute which is a ForeignKey to a StatefulObject
    stateful_object = None
    # Terse human readable verb, e.g. "Change this" (for buttons)
    state_verb = None

    def get_stateful_object_id(self):
        stateful_object = getattr(self, self.stateful_object)
        return stateful_object.pk

    def get_stateful_object(self):
        stateful_object = getattr(self, self.stateful_object)
        # Get a fresh instance every time, we don't want one hanging around in the job
        # run procedure because steps might be modifying it
        stateful_object = stateful_object.__class__._base_manager.get(pk = stateful_object.pk)
        return stateful_object


class NullStep(Step):
    def run(self, kwargs):
        pass


class AnyTargetMountStep(Step):
    def _run_agent_command(self, target, command):
        # There is a set of hosts that we can try to contact to start the target: assume
        # that anything with a TargetMount on is part of the corosync cluster and can be
        # used to issue a command to start this resource.

        # Try and use each targetmount, the one with the most recent successful audit first
        from configure.models import ManagedTargetMount
        available_tms = ManagedTargetMount.objects.filter(target = target, host__state = 'lnet_up').order_by('-host__monitor__last_success')
        if available_tms.count() == 0:
            raise RuntimeError("No hosts are available for target %s" % target)
        available_tms = list(available_tms)

        for tm in available_tms:
            job_log.debug("command '%s' on target %s trying targetmount %s" % (command, target, tm))

            try:
                return self.invoke_agent(tm.host, command)
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
