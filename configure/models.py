from django.db import models

CONFIGURE_MODELS = True
from monitor import models as monitor_models

class StatefulObject(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True

    state = models.CharField(max_length = 32)

    def __init__(self, *args, **kwargs):
        super(StatefulObject, self).__init__(*args, **kwargs)

        if not self.state:
            print "Initializing state"
            self.state = self.initial_state

    def get_deps(self, state = None):
        """Return static dependencies, e.g. a targetmount in state
           mounted has a dependency on a host in state lnet_started but
           can get rid of it by moving to state unmounted"""
        return []

class ManagedTarget(StatefulObject):
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
            deps.append((self.host, 'lnet_up', 'unmounted'))

        if state == 'mounted' or state =='unmounted':
            deps.append((self.target, 'registered', 'unconfigured'))

        return deps

class ManagedHost(monitor_models.Host, StatefulObject):
    states = ['lnet_unloaded', 'lnet_down', 'lnet_up']
    initial_state = 'lnet_unloaded'

# Configure a pair:
#  select two servers
#  

# Create an OST: 


# Create your models here.


# targets: states are configured, formatted, registered, 

# targetmounts: states are configured, deployed+mounted, deployed+unmounted, undeployed

# target transitions:
#configured->formatted
# * requires a primary targetmount
#formatted->registered
# * happens when a targetmount successfully mounts
#registered->

# starting a target:
# states are 
# requires its status to be formatted, unmounted or registered, unmounted
# requires a primary mount point to 
# if formatted, unmounted and this is an OST, additionally require this filesystem's MDT to be registered, mounted or registered, unmounted

# run mount -t lustre... 


# starting a targetmount
# require 

class JobRecord(models.Model):
    paused = models.BooleanField(default = False)
    complete = models.BooleanField(default = False)
    errored = models.BooleanField(default = False)
    cancelled = models.BooleanField(default = False)

    def __init__(self, job, *args, **kwargs):
        super(JobRecord, self).__init__(*args, **kwargs)
        self.job = job
        if self.id != None:
            # TODO: bring back self.steps from persisting it somewhere
            pass

    def set_steps(self, steps):
        self.steps = steps

    def _append_step(self, step):
        from configure.lib.job import Step
        assert isinstance(step, Step), ValueError("%s is not a Step" % step)
        from configure.tasks import run_job_step
        celery_job = run_job_step.apply_async(args = [step])
        step_record = StepRecord(job_record = self, task_id = celery_job.task_id)
        step_record.save()

    def run(self):
        self.save()
        for klass, args in self.steps:
            instance = klass(self, args)
            self._append_step(instance)

        from configure.lib.job import FinalStep
        from configure.tasks import StateChangeJob
        if isinstance(self.job, StateChangeJob):
            print "scheduling final state %s for job %s" % (self.job.__class__.state_transition[2], self.job)
            final_step = FinalStep(self, {
                'stateful_object_class': self.job.stateful_object.__class__.__name__,
                'stateful_object_id': self.job.stateful_object.id,
                'final_state': self.job.__class__.state_transition[2]
                })
        else:
            final_step = FinalStep(self, {})
        self._append_step(final_step)

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

class StepRecord(models.Model):
    job_record = models.ForeignKey(JobRecord)
    # djcelery.models.TaskState stores task_id as UUID
    task_id = models.CharField(max_length=36)

    def retry(self):
        from celery.result import AsyncResult
        return AsyncResult(self.task_id).retry()

    def info(self):
        from celery.result import AsyncResult
        return AsyncResult(self.task_id).info

    def state(self):
        from celery.result import AsyncResult
        return AsyncResult(self.task_id).state

