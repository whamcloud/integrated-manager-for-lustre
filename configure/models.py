from django.db import models

CONFIGURE_MODELS = True
from monitor import models as monitor_models
from polymorphic.models import DowncastMetaclass

class StatefulObject(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True

    state = models.CharField(max_length = 32)

    def __init__(self, *args, **kwargs):
        super(StatefulObject, self).__init__(*args, **kwargs)

        if not self.state:
            self.state = self.initial_state

    def get_deps(self, state = None):
        """Return static dependencies, e.g. a targetmount in state
           mounted has a dependency on a host in state lnet_started but
           can get rid of it by moving to state unmounted"""
        return []

class ManagedTarget(StatefulObject):
    __metaclass__ = DowncastMetaclass
    # unformatted: I exist in theory in the database 
    # formatted: I've been mkfs'd
    # registered: the mgs knows about me
    # removed: this target no longer exists in real life
    states = ['unformatted', 'formatted', 'registered', 'removed']
    initial_state = 'unformatted'
    # Additional states needed for 'deactivated'?

class ManagedOst(monitor_models.ObjectStoreTarget, ManagedTarget):
    def default_mount_path(self, host):
        counter = 0
        while True:
            candidate = "/mnt/%s/ost%d" % (self.filesystem.name, counter)
            try:
                monitor_models.Mountable.objects.get(host = host, mount_point = candidate)
                counter = counter + 1
            except monitor_models.Mountable.DoesNotExist:
                return candidate

class ManagedMdt(monitor_models.MetadataTarget, ManagedTarget):
    def default_mount_path(self, host):
        return "/mnt/%s/mdt" % self.filesystem.name

class ManagedMgs(monitor_models.ManagementTarget, ManagedTarget):
    def default_mount_path(self, host):
        return "/mnt/mgs"

class ManagedTargetMount(monitor_models.TargetMount, StatefulObject):
    # unconfigured: I only exist in theory in the database
    # mounted: I am in fstab on the host and mounted
    # unmounted: I am in fstab on the host and unmounted
    states = ['unconfigured', 'mounted', 'unmounted']
    # TODO: implement fstab configuration, until then start in 'unmounted'
    initial_state = 'unmounted'

    def get_deps(self, state = None):
        if not state:
            state = self.state

        deps = []
        if state == 'mounted':
            deps.append((self.host.managedhost, 'lnet_up', 'unmounted'))

        # This will only make sense once 'unconfigured' is implemented, otherwise
        # we are initially in 'unmounted' and expecting the mgs to be 'registered'
        # before anything's ever happened
        #if state == 'mounted' or state =='unmounted':
        #    deps.append((self.target.downcast(), 'registered', 'unconfigured'))

        return deps

class ManagedHost(monitor_models.Host, StatefulObject):
    states = ['lnet_unloaded', 'lnet_down', 'lnet_up']
    initial_state = 'lnet_unloaded'

class Job(models.Model):
    __metaclass__ = DowncastMetaclass
    paused = models.BooleanField(default = False)
    complete = models.BooleanField(default = False)
    errored = models.BooleanField(default = False)
    cancelled = models.BooleanField(default = False)

    def get_deps(self):
        return []

    def run(self):
        self.save()

        i = 0
        steps = self.get_steps()
        if len(steps) == 0:
            raise RuntimeError("Jobs must have at least 1 step (%s)" % self)

        for klass, args in steps:
            # Create a Step and push it to the 'run_job_step' celery task
            step = klass(self, args)
            if i == len(steps) - 1:
                step.mark_final()
            from configure.lib.job import Step
            assert isinstance(step, Step), ValueError("%s is not a Step" % step)
            from configure.tasks import run_job_step
            print "submitted step %s" % step
            celery_job = run_job_step.apply_async(args = [step])

            # Record this attempt to run a step
            step_record = StepAttempt(
                    job = self,
                    task_id = celery_job.task_id,
                    step_index = i)
            step_record.save()
            i = i + 1

    def pause(self):
        # This will cause any future steps in the queue to reschedule themselves
        self.paused = True
        self.save()

        # Get a list of all incomplete steps
        # if any of them are 


        # TODO: shoot currently running tasks in the head
        # TODO: provide a mechanism for tasks to recover when shot in the head

    def cancel(self):
        # TODO: shoot all tasks in the head
        self.complete = True
        self.cancelled = True
        self.save()

    def unpause(self):
        self.paused = False
        self.save()

    def retry(self):
        """Start running the job from the last step that did not complete
           successfully (i.e. try running the last failed step again"""
        assert(self.complete)
        #assert(at least one non-OK step)

    def restart(self):
        """Start running the job from square 1, even if some steps had
           already completed"""
        assert(self.complete)

    def mark_complete(self):
        if isinstance(self, StateChangeJob):
            new_state = self.state_transition[2]
            obj = self.get_stateful_object()
            obj.state = new_state
            print "StateChangeJob complete, setting state %s on %s" % (new_state, obj)
            obj.save()
        self.complete = True
        self.save()

class StepAttempt(models.Model):
    job = models.ForeignKey(Job)
    step_index = models.PositiveIntegerField()
    # djcelery.models.TaskState stores task_id as UUID
    task_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add = True)

    def info(self):
        from celery.result import AsyncResult
        return AsyncResult(self.task_id).info

    def state(self):
        from celery.result import AsyncResult
        return AsyncResult(self.task_id).state

from configure.lib.job import StateChangeJob

class DependencyAbsent(Exception):
    """A Job wants to depend on something that doesn't exist"""
    pass

class RegisterTargetJob(Job, StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = (ManagedTarget, 'formatted', 'registered')
    target = models.ForeignKey('ManagedTarget')
    stateful_object = 'target'

    def get_steps(self):
        steps = []
        # FIXME: somehow need to avoid advertising this transition for MGS targets
        # currently as hack this is just a no-op for MGSs which marks them registered
        from configure.lib.job import MountStep, UnmountStep, NullStep
        print self.target
        if isinstance(self.target, ManagedMgs):
            steps.append((NullStep, {}))
        if isinstance(self.target, monitor_models.FilesystemMember):
            steps.append((MountStep, {"target_mount_id": self.target.targetmount_set.get(primary = True).id}))
            steps.append((UnmountStep, {"target_mount_id": self.target.targetmount_set.get(primary = True).id}))

        print "register steps=%s" % steps

        return steps

    def get_deps(self):
        deps = []

        # Registering an OST depends on the MDT having already been registered,
        # because in Lustre >= 2.0 MDT registration wipes previous OST registrations
        # such that for first mount you must already do mgs->mdt->osts
        if isinstance(self.target, ManagedOst):
            try:
                mdt = ManagedMdt.objects.get(filesystem = self.target.filesystem)
            except ManagedMdt.DoesNotExist:
                raise DependencyAbsent("Cannot register OSTs for filesystem %s until an MDT is created" % self.target.filesystem)
            deps.append((mdt, "registered"))

        print "register deps"
        if isinstance(self.target, monitor_models.FilesystemMember):
            print "depping mgs"
            mgs = self.target.filesystem.mgs
            deps.append((mgs.targetmount_set.get(primary = True).downcast(), "mounted"))

        return deps

class StartTargetMountJob(Job, StateChangeJob):
    stateful_object = 'target_mount'
    state_transition = (ManagedTargetMount, 'unmounted', 'mounted')
    target_mount = models.ForeignKey(ManagedTargetMount)

    def get_steps(self):
        from configure.lib.job import MountStep
        return [(MountStep, {"target_mount_id": self.target_mount.id})]

class StopTargetMountJob(Job, StateChangeJob):
    stateful_object = 'target_mount'
    state_transition = (ManagedTargetMount, 'mounted', 'unmounted')
    target_mount = models.ForeignKey(ManagedTargetMount)

    def get_steps(self):
        from configure.lib.job import UnmountStep
        return [(UnmountStep, {"target_mount_id": self.target_mount.id})]

class FormatTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    target = models.ForeignKey(ManagedTarget)
    stateful_object = 'target'

    def get_steps(self):
        from configure.lib.job import MkfsStep
        return [(MkfsStep, {'target_id': self.target.id})]

class LoadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)

    def get_steps(self):
        from configure.lib.job import LoadLNetStep
        return [(LoadLNetStep, {'host_id': self.host.id})]

class UnloadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)

    def get_steps(self):
        from configure.lib.job import UnloadLNetStep
        return [(UnloadLNetStep, {'host_id': self.host.id})]
    
class StartLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)

    def get_steps(self):
        from configure.lib.job import StartLNetStep
        return [(StartLNetStep, {'host_id': self.host.id})]

class StopLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)

    def get_steps(self):
        from configure.lib.job import StopLNetStep
        return [(StopLNetStep, {'host_id': self.host.id})]

class StartFilesystemJob(Job):
    filesystem = models.ForeignKey(monitor_models.Filesystem)

    def get_steps(self):
        mgs = self.filesystem.mgs
        mdt = ManagedMdt.objects.get(filesystem = self.filesystem)
        ost_list = ManagedOst.objects.filter(filesystem = self.filesystem)

        steps = []
        steps.append((MountStep, {'target_mount_id': mgs.targetmount_set.get(primary = True).id}))
        steps.append((MountStep, {'target_mount_id': mdt.targetmount_set.get(primary = True).id}))
        steps.extend([(MountStep, {'target_mount_id': ost.targetmount_set.get(primary = True).id}) for ost in ost_list])

        return steps

class StopFilesystemJob(Job):
    filesystem = models.ForeignKey(monitor_models.Filesystem)

    def get_steps(self):
        mgs = self.filesystem.mgs
        mdt = ManagedMdt.objects.get(filesystem = self.filesystem)
        ost_list = ManagedOst.objects.filter(filesystem = self.filesystem)

        steps = []
        steps.append((UnmountStep, {'target_mount_id': mgs.targetmount_set.get(primary = True).id}))
        steps.append((UnmountStep, {'target_mount_id': mdt.targetmount_set.get(primary = True).id}))
        steps.extend([(UnmountStep, {'target_mount_id': ost.targetmount_set.get(primary = True).id}) for ost in ost_list])

        return steps

