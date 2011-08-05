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
    initial_state = 'unconfigured'

    def __str__(self):
        if self.primary:
            kind_string = "primary"
        else:
            kind_string = "failover"

        return "%s:%s:%s" % (self.host, kind_string, self.target)

    def get_deps(self, state = None):
        if not state:
            state = self.state

        deps = []
        if state == 'mounted':
            deps.append((self.host.managedhost, 'lnet_up', 'unmounted'))

        # We allow an 'unmounted' targetmount for a target which is not
        # registered, because creating the targetmount is a necessary
        # part of registration
        if state == 'mounted':
            deps.append((self.target.downcast(), 'registered', 'unmounted'))

        return deps

class ManagedHost(monitor_models.Host, StatefulObject):
    states = ['lnet_unloaded', 'lnet_down', 'lnet_up']
    initial_state = 'lnet_unloaded'

class Job(models.Model):
    __metaclass__ = DowncastMetaclass

    states = ('pending', 'tasked', 'complete')
    state = models.CharField(max_length = 16, default = 'pending')

    errored = models.BooleanField(default = False)
    paused = models.BooleanField(default = False)
    cancelled = models.BooleanField(default = False)

    created_at = models.DateTimeField(auto_now_add = True)

    dependencies = models.ManyToManyField('Job')

    class DependenciesFailed(Exception):
        pass

    def ready_to_run(self):
        for dep in self.dependencies.all():
            if dep.state == 'pending':
                return False
        return True 

    from django.db import transaction
    @staticmethod
    @transaction.commit_on_success
    def run_next():
        # If there's already something underway, then no need to run anything
        running_jobs = Job.objects.filter(state = 'tasked').count()
        if running_jobs > 0:
            return

        # Choose the next Job to run
        # TODO: respect paused flag (should it hold up the queue or 
        # just prevent that one job from executing?)
        for job in Job.objects.filter(state = 'pending').order_by('created_at'):
            deps_done = True
            for dep in job.dependencies.all():
                if dep.state == 'pending':
                    if dep.ready_to_run():
                        try:
                            dep.run()
                            return
                        except Exception,e:
                            print "Exception %s" % e
                            pass
                    else:
                        deps_done = False

            if deps_done:
                try:
                    job.run()
                    return
                except Exception, e:
                    print "Exception %s" % e

    def get_deps(self):
        return []

    def run(self):
        print "Job.run %s" % self
        assert(self.state == 'pending')

        # So that someone can do SomeJob().run()
        if not self.pk:
            self.save()
        else:
            print self.pk

        # Check my dependencies are complete and successful
        for dep in self.dependencies.all():
            if not (dep.state == 'complete' and dep.errored == False):
                self.state = 'complete'
                self.errored = True
                self.save()
                print "Cancelling job %s because dependency %s is errored" % (self, dep)
                raise Job.DependenciesFailed()

        self.state = 'tasked'
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
        # In case of races, ignore someone trying to pause a 
        # task which has completed
        if self.state == 'complete':
            return
       
        assert(self.state == 'tasked')
        #self.paused = True
        # TODO: kill the currently active task if it's idempotent (we'll run 
        # it again when we resume) or let it finish if not.

    def retry(self):
        """Start running the job from the last step that did not complete
           successfully (i.e. try running the last failed step again"""
        assert(self.state == 'complete')
        # TODO

    def restart(self):
        """Start running the job from square 1, even if some steps had
           already completed"""
        assert(self.state == 'complete')
        # TODO

    def mark_errored(self):
        # TODO: revoke celery tasks
        # (currently tasks check the errored flag on run)
        # NB: if we allow restarting an errored task then we need to make sure
        # that any tasks from the first run aren't hanging around and going to 
        # run when we clear the errored flag
        print "mark errored %s" % self
        self.state = 'complete'
        self.errored = True
        self.save()
        Job.run_next()

    def mark_complete(self):
        if isinstance(self, StateChangeJob):
            new_state = self.state_transition[2]
            obj = self.get_stateful_object()
            obj.state = new_state
            print "StateChangeJob complete, setting state %s on %s" % (new_state, obj)
            obj.save()
        self.state = 'complete'
        self.save()
        Job.run_next()

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

class ConfigureTargetMountJob(Job, StateChangeJob):
    state_transition = (ManagedTargetMount, 'unconfigured', 'unmounted')
    stateful_object = 'target_mount'
    state_verb = "Configure"
    target_mount = models.ForeignKey('ManagedTargetMount')

    def description(self):
        return "Configuring mount %s on %s" % (self.target_mount.mount_point, self.target_mount.host)

    def get_steps(self):
        from configure.lib.job import MkdirStep
        return [(MkdirStep, {'target_mount_id': self.target_mount.id})]

class RegisterTargetJob(Job, StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = (ManagedTarget, 'formatted', 'registered')
    stateful_object = 'target'
    state_verb = "Register"
    target = models.ForeignKey('ManagedTarget')

    def description(self):
        target = self.target.downcast()
        if isinstance(target, ManagedMgs):
            return "Register MGS"
        elif isinstance(target, ManagedOst):
            return "Register OST to filesystem %s" % target.filesystem.name
        elif isinstance(target, ManagedMdt):
            return "Register MDT to filesystem %s" % target.filesystem.name
        else:
            raise NotImplementedError()

    def get_steps(self):
        steps = []
        # FIXME: somehow need to avoid advertising this transition for MGS targets
        # currently as hack this is just a no-op for MGSs which marks them registered
        from configure.lib.job import MountStep, UnmountStep, NullStep
        target = self.target.downcast()
        if isinstance(target, ManagedMgs):
            steps.append((NullStep, {}))
        if isinstance(target, monitor_models.FilesystemMember):
            steps.append((MountStep, {"target_mount_id": target.targetmount_set.get(primary = True).id}))
            steps.append((UnmountStep, {"target_mount_id": target.targetmount_set.get(primary = True).id}))

        print "register steps=%s" % steps

        return steps

    def get_deps(self):
        deps = []

        deps.append((self.target.targetmount_set.get(primary = True).host.downcast(), 'lnet_up'))

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

        # Depend on state 'unmounted' to make sure it's configured (i.e. mount point exists)
        deps.append((self.target.targetmount_set.get(primary = True).downcast(), "unmounted"))

        return deps

class StartTargetMountJob(Job, StateChangeJob):
    stateful_object = 'target_mount'
    state_transition = (ManagedTargetMount, 'unmounted', 'mounted')
    state_verb = "Start"
    target_mount = models.ForeignKey(ManagedTargetMount)

    def description(self):
        return "Starting target %s" % self.target_mount.target

    def get_steps(self):
        from configure.lib.job import MountStep
        return [(MountStep, {"target_mount_id": self.target_mount.id})]

class StopTargetMountJob(Job, StateChangeJob):
    stateful_object = 'target_mount'
    state_transition = (ManagedTargetMount, 'mounted', 'unmounted')
    state_verb = "Stop"
    target_mount = models.ForeignKey(ManagedTargetMount)

    def description(self):
        return "Stopping target %s" % self.target_mount.target

    def get_steps(self):
        from configure.lib.job import UnmountStep
        return [(UnmountStep, {"target_mount_id": self.target_mount.id})]

class FormatTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    target = models.ForeignKey(ManagedTarget)
    stateful_object = 'target'
    state_verb = 'Format'

    def description(self):
        target = self.target.downcast()
        if isinstance(target, ManagedMgs):
            return "Formatting MGS on %s" % target.targetmount_set.get(primary = True).host
        elif isinstance(target, ManagedMdt):
            return "Formatting MDT for filesystem %s" % target.filesystem.name
        elif isinstance(target, ManagedOst):
            return "Formatting OST for filesystem %s" % target.filesystem.name
        else:
            raise NotImplementedError()

    def get_steps(self):
        from configure.lib.job import MkfsStep
        return [(MkfsStep, {'target_id': self.target.id})]

class LoadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Load LNet'

    def description(self):
        return "Loading LNet module on %s" % self.host

    def get_steps(self):
        from configure.lib.job import LoadLNetStep
        return [(LoadLNetStep, {'host_id': self.host.id})]

class UnloadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Unload LNet'

    def description(self):
        return "Unloading LNet module on %s" % self.host

    def get_steps(self):
        from configure.lib.job import UnloadLNetStep
        return [(UnloadLNetStep, {'host_id': self.host.id})]
    
class StartLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Start LNet'

    def description(self):
        return "Start LNet on %s" % self.host

    def get_steps(self):
        from configure.lib.job import StartLNetStep
        return [(StartLNetStep, {'host_id': self.host.id})]

class StopLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Stop LNet'

    def description(self):
        return "Stop LNet on %s" % self.host

    def get_steps(self):
        from configure.lib.job import StopLNetStep
        return [(StopLNetStep, {'host_id': self.host.id})]

