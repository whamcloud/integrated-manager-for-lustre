from django.db import models

CONFIGURE_MODELS = True
from monitor import models as monitor_models
from polymorphic.models import DowncastMetaclass

MAX_STATE_STRING = 32


from logging import getLogger, FileHandler, StreamHandler, DEBUG
getLogger('Job').setLevel(DEBUG)
getLogger('Job').addHandler(FileHandler("Job.log"))
getLogger('Job').addHandler(StreamHandler())

class StatefulObject(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True

    state = models.CharField(max_length = MAX_STATE_STRING)
    states = None
    initial_state = None

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
        elif not self.block_device:
            kind_string = "failover_nodev"
        else:
            kind_string = "failover"

        return "%s:%s:%s" % (self.host, kind_string, self.target)

    def get_deps(self, state = None):
        if not state:
            state = self.state

        deps = []
        if state == 'mounted':
            deps.append((self.host.managedhost, 'lnet_up', 'unmounted'))
            from django.db.models import Q
            for tm in self.target.targetmount_set.filter(~Q(pk = self.id)):
                deps.append((tm, 'unmounted', 'unmounted'))

        if state == 'mounted':
            deps.append((self.target.downcast(), 'registered', 'unmounted'))

        return deps

class ManagedHost(monitor_models.Host, StatefulObject):
    states = ['lnet_unloaded', 'lnet_down', 'lnet_up']
    initial_state = 'lnet_unloaded'

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
class StateLock(models.Model):
    __metaclass__ = DowncastMetaclass
    job = models.ForeignKey('Job')

    locked_item_type = models.ForeignKey(ContentType, related_name = 'locked_item')
    locked_item_id = models.PositiveIntegerField()
    locked_item = GenericForeignKey('locked_item_type', 'locked_item_id')

    @classmethod
    def filter_by_locked_item(cls, stateful_object):
        ctype = ContentType.objects.get_for_model(stateful_object)
        return cls.objects.filter(locked_item_type = ctype, locked_item_id = stateful_object.id)

class StateReadLock(StateLock):
    locked_state = models.CharField(max_length = MAX_STATE_STRING)

class StateWriteLock(StateLock):
    begin_state = models.CharField(max_length = MAX_STATE_STRING)
    end_state = models.CharField(max_length = MAX_STATE_STRING)

# Lock is the wrong word really, these objects exist for the lifetime of the Job, 
# to allow 
# All locks depend on the last pending job to write to a stateful object on which
# they hold claim read or write lock.

class Test(models.Model):
    i = models.IntegerField(default = 0)

def job_log(string):
    import os
    string = "%s: %s" % (os.getpid(), string)
    getLogger('Job').info(string)

class Job(models.Model):
    __metaclass__ = DowncastMetaclass

    states = ('pending', 'tasked', 'complete')
    state = models.CharField(max_length = 16, default = 'pending')

    errored = models.BooleanField(default = False)
    paused = models.BooleanField(default = False)
    cancelled = models.BooleanField(default = False)

    created_at = models.DateTimeField(auto_now_add = True)

    wait_for_count = models.PositiveIntegerField(default = 0)
    wait_for_completions = models.PositiveIntegerField(default = 0)
    wait_for = models.ManyToManyField('Job', symmetrical = False, related_name = 'wait_for_job')

    depend_on_count = models.PositiveIntegerField(default = 0)
    depend_on_completions = models.PositiveIntegerField(default = 0)
    depend_on = models.ManyToManyField('Job', symmetrical = False, related_name = 'depend_on_job')

    def notify_wait_for_complete(self):
        """Called by a wait_for job to notify that it is complete"""
        from django.db.models import F
        Job.objects.get_or_create(pk = self.id)
        Job.objects.filter(pk = self.id).update(wait_for_completions = F('wait_for_completions')+1)
   
    def notify_depend_on_complete(self):
        """Called by a depend_on job to notify that it is complete"""
        from django.db.models import F
        Job.objects.get_or_create(pk = self.id)
        Job.objects.filter(pk = self.id).update(depend_on_completions = F('depend_on_completions')+1)
   

    def create_dependencies(self):
        """Examine overlaps between self's statelocks and those of 
           earlier jobs which are still pending, and generate wait_for
           dependencies when we have a write lock and they have a read lock
           or generate depend_on dependencies when we have a read or write lock and
           they have a write lock"""
        from django.db.models import Q
        from configure.models import Job

        for lock in self.statelock_set.all():
            if isinstance(lock, StateWriteLock):
                wl = lock
                # Depend on the most recent pending write to this stateful object,
                # trust that it will have depended on any before that.
                try:
                    prior_write_lock = StateWriteLock.filter_by_locked_item(wl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).latest('id')
                    assert(wl.begin_state == prior_write_lock.end_state)
                    self.depend_on.add(prior_write_lock.job)
                    # We will only wait_for read locks after this write lock, as it
                    # will have wait_for'd any before it.
                    read_barrier_id = prior_write_lock.job.id
                except StateWriteLock.DoesNotExist:
                    print "No prior write locks for write lock %s of job %s" % (wl, self)
                    read_barrier_id = 0
                    pass

                # Wait for any reads of the stateful object between the last write and
                # our position.
                prior_read_locks = StateWriteLock.filter_by_locked_item(wl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).filter(job__id__gte = read_barrier_id)
                for i in prior_read_locks:
                    self.wait_for.add(i.job)
            elif isinstance(lock, StateReadLock):
                rl = lock
                try:
                    prior_write_lock = StateWriteLock.filter_by_locked_item(rl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).latest('id')
                    assert(prior_write_lock.end_state == rl.locked_state)
                    self.depend_on.add(prior_write_lock.job)
                except StateWriteLock.DoesNotExist:
                    print "No prior write locks for read lock %s of job %s" % (rl, self)
                    pass

        self.wait_for_count = self.wait_for.count()
        self.depend_on_count = self.depend_on.count()
        self.save()

    def create_locks(self):
        from configure.lib.job import StateChangeJob
        # Take read lock on everything from self.get_deps
        for d in self.get_deps():
            depended_on, depended_state = d
            StateReadLock.objects.create(job = self, locked_item = depended_on, locked_state = depended_state)

        if isinstance(self, StateChangeJob):
            stateful_object = self.get_stateful_object()
            target_klass, old_state, new_state = self.state_transition

            # Take read lock on everything from get_stateful_object's get_deps if 
            # this is a StateChangeJob
            for d in stateful_object.get_deps(new_state):
                depended_on, depended_state, fix_state = d
                StateReadLock.objects.create(job = self, locked_item = depended_on, locked_state = depended_state)

            # Take a write lock on get_stateful_object if this is a StateChangeJob
            StateWriteLock.objects.create(job = self, locked_item = self.get_stateful_object(), begin_state = old_state, end_state = new_state)

    @classmethod
    def run_next(cls):
        from django.db.models import F
        runnable_jobs = Job.objects \
            .filter(wait_for_completions = F('wait_for_count')) \
            .filter(depend_on_completions = F('depend_on_count')) \
            .filter(state = 'pending')

        getLogger('Job').info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (runnable_jobs.count(), Job.objects.filter(state = 'pending').count(), Job.objects.filter(state = 'tasked').count()))
        for job in runnable_jobs:
            print "%d %d" % (job.wait_for_count, job.wait_for_completions)
            print "%d %d" % (job.depend_on_count, job.depend_on_completions)
            print job.state
            job.run()

    def get_deps(self):
        return []

    def get_steps(self):
        raise NotImplementedError()

    def run(self):
        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.
        updated = Job.objects.filter(pk = self.id, state = 'pending').update(state = 'tasked')

        if updated == 0:
            # Someone else already started this job, bug out
            print "updated == 0"
            return
        assert(updated == 1)

        print "Job.run %s" % self
        job_log("Job.run %d" % self.id)

        # My wait_for are complete, and I don't care if they're errored, just
        # that they aren't running any more.
        # My depend_on, however, must have completed successfully in order
        # to guarantee that my state dependencies have been met, so I will
        # error out if any depend_on are errored.
        for dep in self.depend_on.all():
            assert(dep.state == 'complete')
            if dep.errored:
                self.state = 'complete'
                self.errored = True
                self.save()
                print "Cancelling job %s because depend_on %s is errored" % (self, dep)
                return

        self.state = 'tasked'
        self.save()

        self.run_step(0)

    def run_step(self, idx):
        print "run_step %d" % idx
        i = 0
        steps = self.get_steps()
        if len(steps) == 0:
            raise RuntimeError("Jobs must have at least 1 step (%s)" % self)

        for klass, args in steps:
            # Create a Step and push it to the 'run_job_step' celery task
            step = klass(self, args)
            if i == len(steps) - 1:
                step.mark_final()
            step.index = i
            from configure.lib.job import Step
            assert isinstance(step, Step), ValueError("%s is not a Step" % step)
            from configure.tasks import run_job_step

            if i == idx:
                print "submitted step %d:%s" % (i,step)
                celery_job = run_job_step.delay(step)

                # FIXME: this is just for debug before we have retry:
                # consistency check that we're not adding extra tasks
                try:
                    existing = self.stepattempt_set.get(step_index = i)
                    raise RuntimeError("Trying to double submit step %d of job %d" % (i, self.id))
                except:
                    pass


                # Record this attempt to run a step
                self.stepattempt_set.create(
                        task_id = celery_job.task_id,
                        step_index = i)
            else:
                print "passing over step %d" % i
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

    def mark_complete(self, errored = False):
        if not errored and isinstance(self, StateChangeJob):
            new_state = self.state_transition[2]
            obj = self.get_stateful_object()
            obj.state = new_state
            print "StateChangeJob complete, setting state %s on %s" % (new_state, obj)
            obj.save()

        self.state = 'complete'
        self.errored = errored
        self.save()

        getLogger('Job').info("job %d complete, notifying dependents" % self.id)
        for dependent in self.depend_on_job.all():
            dependent.notify_depend_on_complete()
        for dependent in self.wait_for_job.all():
            dependent.notify_wait_for_complete()

        from django.db import transaction
        transaction.commit()
        Job.run_next()

    def description(self):
        raise NotImplementedError

    def __str__(self):
        try:
            return "%s (Job %d)" % (self.description(), self.id)
        except NotImplementedError:
            return "<Job %d>" % self.id

class StepAttempt(models.Model):
    job = models.ForeignKey(Job)
    step_index = models.PositiveIntegerField()
    # djcelery.models.TaskState stores task_id as UUID
    task_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add = True)

    def debug_step(self):
        return self.job.downcast().get_steps()[self.step_index]
    
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

    def create_locks(self, *args, **kwargs):
        # Create a write lock on the target mount that we're going to 
        # mount and unmount in order to register this target
        tm = self.target.targetmount_set.get(primary = True)
        # NB because we also depend on it in get_deps, we will also be 
        # holding a read lock on it.  Little messy but isn't invalid.  Will 
        # potentially result in downstream jobs both wait_for'ing and depend_on'ing
        # the same job.
        StateWriteLock(job = self, locked_item = tm,
                begin_state = 'unmounted', end_state = 'unmounted').save()
        super(RegisterTargetJob, self).create_locks(*args, **kwargs)

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

        if isinstance(self.target, monitor_models.FilesystemMember):
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

