
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json
from re import escape

import logging
import settings
import time

from configure.lib.agent import Agent

job_log = logging.getLogger('job')
job_log.setLevel(logging.DEBUG)
handler = logging.FileHandler(settings.JOB_LOG_PATH)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
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
    def __init__(self, stateful_object, preferred_state, acceptable_states = None, fix_state = None):
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
        result = self.stateful_object.state in self.acceptable_states
        return self.stateful_object.state in self.acceptable_states

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

class StepPaused(Exception):
    """A step did not execute because the job is paused."""
    pass

class StepAborted(Exception):
    """A step did not execute because the job has errored."""
    pass

class StepFailed(Exception):
    """A step executed and returned an exception.  The job has been marked as errored."""
    def __init__(self, step_exception):
        self.step_exception = step_exception
    pass

class StepCleanError(Exception):
    """A step encountered an error which prevented it making any changes,
       such the step may be retried at will.  For example, an attempt to
       mkfs over ssh failed to establish a connection: there is no risk that
       mkfs command started running"""
    pass

class StepDirtyError(Exception):
    """A step encountered an error which may have left the system in 
       an inconsistent state.  For example, connectivity was lost partway
       through a mkfs operation: we don't know if the filesystem is formatted
       or not"""
    pass


STEP_PAUSE_DELAY = 10

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
        steps = self.get_steps()
        # Which one failed?

    def invoke_agent(self, host, command):
        def console_callback(chunk):
            self.result.console = self.result.console + chunk
            self.result.save()
        agent = Agent(job_log, console_callback = console_callback)
        return agent.invoke(host, command)

class StateChangeJob(object):
    """Subclasses must define a class attribute 'stateful_object'
       identifying another attribute which returns a StatefulObject"""

    # Tuple of (StatefulObjectSubclass, old_state, new_state)
    state_transition = None
    # Name of an attribute which is a ForeignKey to a StatefulObject
    stateful_object = None
    # Terse human readable verb, e.g. "Change this" (for buttons)
    state_verb = None

    def get_stateful_object(self):
        from configure.models import StatefulObject
        stateful_object = getattr(self, self.stateful_object)

        # Get a fresh instance every time, we don't want one hanging around in the job
        # run procedure because steps might be modifying it
        stateful_object = stateful_object.__class__._base_manager.get(pk = stateful_object.pk).downcast()
        assert(isinstance(stateful_object, StatefulObject))
        return stateful_object

class MkfsStep(Step):
    def _mkfs_args(self, target):
        from monitor.models import FilesystemMember
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst
        kwargs = {}
        primary_mount = target.targetmount_set.get(primary = True)

        kwargs['target_types'] = {
            ManagedMgs: "mgs",
            ManagedMdt: "mdt",
            ManagedOst: "ost"
            }[target.__class__]

        if isinstance(target, FilesystemMember):
            kwargs['fsname'] = target.filesystem.name
            assert(len(target.filesystem.mgs_nids()) > 0)
            kwargs['mgsnode'] = target.filesystem.mgs_nids()

        kwargs['reformat'] = True

        for secondary_mount in target.targetmount_set.filter(primary = False):
            host = secondary_mount.host
            nids = [n.nid_string for n in host.nid_set.all()]
            if len(nids) > 0:
                kwargs['failnode'] = nids

        kwargs['device'] = primary_mount.block_device.path

        return kwargs

    @classmethod
    def describe(cls, kwargs):
        from monitor.models import Target
        target_id = kwargs['target_id']
        target = Target.objects.get(id = target_id).downcast()
        target_mount = target.targetmount_set.get(primary = True)
        return "Format %s on %s" % (target, target_mount.host)
    
    def run(self, kwargs):
        from monitor.models import Target, Lun
        from configure.models import ManagedTarget

        target_id = kwargs['target_id']
        target = Target.objects.get(id = target_id).downcast()

        assert(isinstance(target, ManagedTarget))
        target_mount = target.targetmount_set.get(primary = True)
        # This is a primary target mount so must have a LunNode
        assert(target_mount.block_device != None)

        args = self._mkfs_args(target)
        result = self.invoke_agent(target_mount.host, "format-target --args %s" % escape(json.dumps(args)))
        fs_uuid = result['uuid']
        lun_node = target_mount.block_device
        if lun_node.lun:
            job_log.debug("Updating target_mount %s Lun after formatting with uuid %s" % (target_mount, fs_uuid))
            lun = lun_node.lun
            lun.fs_uuid = fs_uuid
            lun.save()
        else:
            job_log.debug("Creating target_mount %s Lun after formatting with uuid %s" % (target_mount, fs_uuid))
            lun = Lun(fs_uuid = fs_uuid)
            lun.save()
            lun_node.lun = lun
            lun_node.save()

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
        from configure.lib.job import StepCleanError
        for tm in ManagedTargetMount.objects.filter(target = target, host__managedhost__state = 'lnet_up', state = 'configured').order_by('-host__monitor__last_success'):
            job_log.debug("command '%s' on target %s trying targetmount %s" % (command, target, tm))
            
            try:
                self.invoke_agent(tm.host, command)
                # Success!
                return
            except Exception, e:
                job_log.warning("Cannot run '%s' on %s." % (command, tm.host))
                # Failure, keep trying TargetMounts

        job_log.error("No targetmounts of target %s could run '%s'." % (target, command))
        # Fall through, none succeeded
        raise StepCleanError()

class MountStep(AnyTargetMountStep):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import Target
        target_id = kwargs['target_id']
        target = Target.objects.get(id = target_id)

        self._run_agent_command(target, "start-target --label %s" % target.name)

class UnmountStep(AnyTargetMountStep):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import Target
        target_id = kwargs['target_id']
        target = Target.objects.get(id = target_id)

        self._run_agent_command(target, "stop-target --label %s" % target.name)

class RegisterTargetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import TargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

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
        from monitor.models import TargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

        # target.name should have been populated by RegisterTarget
        assert(target_mount.block_device != None and target_mount.target.name != None)

        self.invoke_agent(target_mount.host, "configure-ha --device %s --label %s %s --mountpoint %s" % (
                                    target_mount.block_device.path,
                                    target_mount.target.name,
                                    target_mount.primary and "--primary" or "",
                                    target_mount.mount_point))

class UnconfigurePacemakerStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import TargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

        # we would never have succeeded configuring in the first place if target
        # didn't have its name
        assert(target_mount.target.name != None)

        self.invoke_agent(target_mount.host, "unconfigure-ha --label %s %s" % (
                                    target_mount.target.name,
                                    target_mount.primary and "--primary" or ""))

class StartLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "start-lnet")

class StopLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "stop-lnet")

class LoadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "load-lnet")

class UnloadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])
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
        from monitor.models import Target
        Target.delete(kwargs['target_id'])

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

class AddHostStep(Step):
    def is_idempotent(self):
        return False

    def run(self, kwargs):
        from configure.models import ManagedHost
        from os import uname
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "configure-rsyslog --node %s" % uname()[1])

