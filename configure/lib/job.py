
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json
from re import escape

import logging
import settings

from configure.lib.agent import Agent

job_log = logging.getLogger('job')
job_log.setLevel(logging.DEBUG)
handler = logging.FileHandler(settings.JOB_LOG_PATH)
handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(message)s',
        '%d/%b/%Y:%H:%M:%S'))
job_log.addHandler(handler)
if settings.DEBUG:
    job_log.setLevel(logging.DEBUG)
    job_log.addHandler(logging.StreamHandler())
else:
    job_log.setLevel(logging.INFO)


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

    def satisfied(self):
        satisfied = self.stateful_object.state in self.acceptable_states
        if not satisfied:
            job_log.warning("DependOn not satisfied: %s in state %s, not one of %s" %
                    (self.stateful_object,
                     self.stateful_object.state,
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

    def is_idempotent(self):
        """Indicate whether the step is idempotent.  For example, mounting
           a target.  Step subclasses which are idempotent should override this and
           return True."""
        return False

    def run(self, kwargs):
        raise NotImplementedError

    def retry(self):
        pass
        # TODO
        #steps = self.get_steps()
        # Which one failed?

    def invoke_agent(self, host, command):
        def console_callback(chunk):
            self.result.console = self.result.console + chunk
            self.result.save()
        agent = Agent(host = host, log = job_log, console_callback = console_callback)
        return agent.invoke(command)


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


class MkfsStep(Step):
    def _mkfs_args(self, target):
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst, FilesystemMember
        kwargs = {}
        primary_mount = target.managedtargetmount_set.get(primary = True)

        kwargs['target_types'] = {
            ManagedMgs: "mgs",
            ManagedMdt: "mdt",
            ManagedOst: "ost"
            }[target.__class__]

        if isinstance(target, FilesystemMember):
            kwargs['fsname'] = target.filesystem.name
            kwargs['mgsnode'] = target.filesystem.mgs.nids()

        kwargs['reformat'] = True

        fail_nids = []
        for secondary_mount in target.managedtargetmount_set.filter(primary = False):
            host = secondary_mount.host
            failhost_nids = host.lnetconfiguration.get_nids()
            assert(len(failhost_nids) != 0)
            fail_nids.extend(failhost_nids)
        if len(fail_nids) > 0:
            kwargs['failnode'] = fail_nids

        kwargs['device'] = primary_mount.block_device.path

        return kwargs

    @classmethod
    def describe(cls, kwargs):
        from configure.models import ManagedTarget
        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id).downcast()
        target_mount = target.managedtargetmount_set.get(primary = True)
        return "Format %s on %s" % (target, target_mount.host)

    def run(self, kwargs):
        from configure.models import ManagedTarget

        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id).downcast()

        target_mount = target.managedtargetmount_set.get(primary = True)
        # This is a primary target mount so must have a LunNode
        assert(target_mount.block_device != None)

        args = self._mkfs_args(target)
        result = self.invoke_agent(target_mount.host, "format-target --args %s" % escape(json.dumps(args)))
        fs_uuid = result['uuid']
        target.uuid = fs_uuid
        target.save()


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


class MountStep(AnyTargetMountStep):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedTarget, ManagedHost, ManagedTargetMount
        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id)

        result = self._run_agent_command(target, "start-target --label %s --serial %s" % (target.name, target.pk))
        try:
            started_on = ManagedHost.objects.get(fqdn = result['location'])
        except ManagedHost.DoesNotExist:
            job_log.error("Target %s (%s) found on host %s, which is not a ManagedHost" % (target, target_id, result['location']))
            raise
        try:
            target.set_active_mount(target.managedtargetmount_set.get(host = started_on))
        except ManagedTargetMount.DoesNotExist:
            job_log.error("Target %s (%s) found on host %s (%s), which has no ManagedTargetMount for this target" % (target, target_id, started_on, started_on.pk))
            raise

            raise


class UnmountStep(AnyTargetMountStep):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedTarget
        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id)

        self._run_agent_command(target, "stop-target --label %s --serial %s" % (target.name, target.pk))
        target.set_active_mount(None)


class RegisterTargetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedTargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = ManagedTargetMount.objects.get(id = target_mount_id)

        result = self.invoke_agent(target_mount.host, "register-target --device %s --mountpoint %s" % (target_mount.block_device.path, target_mount.mount_point))
        label = result['label']
        target = target_mount.target
        job_log.debug("Registration complete, updating target %d with name=%s" % (target.id, label))
        target.name = label
        target.save()


class ConfigurePacemakerStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedTargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = ManagedTargetMount.objects.get(id = target_mount_id)

        # target.name should have been populated by RegisterTarget
        assert(target_mount.block_device != None and target_mount.target.name != None)

        self.invoke_agent(target_mount.host, "configure-ha --device %s --label %s --uuid %s --serial %s %s --mountpoint %s" % (
                                    target_mount.block_device.path,
                                    target_mount.target.name,
                                    target_mount.target.uuid,
                                    target_mount.target.pk,
                                    target_mount.primary and "--primary" or "",
                                    target_mount.mount_point))


class UnconfigurePacemakerStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedTargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = ManagedTargetMount.objects.get(id = target_mount_id)

        # we would never have succeeded configuring in the first place if target
        # didn't have its name
        assert(target_mount.target.name != None)

        self.invoke_agent(target_mount.host, "unconfigure-ha --label %s --uuid %s --serial %s %s" % (
                                    target_mount.target.name,
                                    target_mount.target.uuid,
                                    target_mount.target.pk,
                                    target_mount.primary and "--primary" or ""))


class StartLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "start-lnet")


class StopLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "stop-lnet")


class LoadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "load-lnet")


class UnloadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "unload-lnet")


class ConfParamStep(Step):
    def is_idempotent(self):
        return False

    def run(self, kwargs):
        from configure.models import ConfParam
        conf_param = ConfParam.objects.get(pk = kwargs['conf_param_id']).downcast()

        self.invoke_agent(conf_param.mgs.primary_server(),
                "set-conf-param --args %s" % escape(json.dumps({
                    'key': conf_param.get_key(), 'value': conf_param.value})))


class ConfParamVersionStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedMgs
        ManagedMgs.objects.\
            filter(pk = kwargs['mgs_id']).\
            update(conf_param_version_applied = kwargs['version'])


class DeleteTargetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedTarget
        ManagedTarget.delete(kwargs['target_id'])


class DeleteTargetMountStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedTargetMount
        ManagedTargetMount.delete(kwargs['target_mount_id'])


class DeleteFilesystemStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedFilesystem
        ManagedFilesystem.delete(kwargs['filesystem_id'])


class DeleteHostStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedHost
        ManagedHost.delete(kwargs['host_id'])
