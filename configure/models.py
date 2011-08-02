from django.db import models

CONFIGURE_MODELS = True
from monitor import models as monitor_models



class ConfiguredTarget(models.Model):
    states = ['configured', 'formatted', 'registered', 'removed']
    # Additional states needed for 'deactivated'?

    state = models.CharField(max_length = 32,
            choices = [(s,s) for s in states])

class ManagedOst(monitor_models.ObjectStoreTarget, ConfiguredTarget):
    def default_mount_path(self, host):
        counter = 0
        while True:
            candidate = "/mnt/%s/ost%d" % (self.filesystem.name, counter)
            try:
                monitor_models.Mountable.objects.get(host = host, mount_point = candidate)
                counter = counter + 1
            except monitor_models.Mountable.DoesNotExist:
                return candidate

class ManagedMdt(monitor_models.MetadataTarget, ConfiguredTarget):
    def default_mount_path(self, host):
        return "/mnt/%s/mdt" % self.filesystem.name

class ManagedMgs(monitor_models.ManagementTarget, ConfiguredTarget):
    def default_mount_path(self, host):
        return "/mnt/mgs"



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

    def __init__(self, *args, **kwargs):
        super(JobRecord, self).__init__(*args, **kwargs)
        if self.id != None:
            # TODO: bring back self.steps
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
        step = FinalStep(self, {})
        self._append_step(step)

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

