#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import threading
import datetime
import sys
import traceback
from dateutil import tz
import dateutil.parser

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q

from chroma_core.lib.cache import ObjectCache
from chroma_core.models import Command, StateLock, ConfigureLNetJob, ManagedHost, ManagedMdt, FilesystemMember, GetLNetStateJob, ManagedTarget, ApplyConfParams, ManagedOst, Job, DeletableStatefulObject, StepResult, StateChangeJob
from chroma_core.services.job_scheduler.dep_cache import DepCache
from chroma_core.services.job_scheduler.lock_cache import LockCache
from chroma_core.services.job_scheduler.state_manager import ModificationOperation
from chroma_core.lib.job import job_log


class RunJobThread(threading.Thread):
    def __init__(self, job_scheduler, job):
        super(RunJobThread, self).__init__()
        self.job = job
        self._job_scheduler = job_scheduler

    def run(self):
        job_log.info("Job %d: %s.run" % (self.job.id, self.__class__.__name__))

        try:
            steps = self.job.get_steps()
        except Exception, e:
            job_log.error("Job %d: exception in get_steps" % self.job.id)
            exc_info = sys.exc_info()
            job_log.error('\n'.join(traceback.format_exception(*(exc_info or sys.exc_info()))))
            self._job_scheduler.complete_job(self.job, errored = True)
            return None

        step_index = 0
        finish_step = -1
        while step_index < len(steps):
            klass, args = steps[step_index]

            result = StepResult(
                step_klass = klass,
                args = args,
                step_index = step_index,
                step_count = len(steps),
                job = self.job)
            result.save()

            step = klass(self.job, args, result)

            from chroma_core.lib.agent import AgentException
            try:
                job_log.debug("Job %d running step %d" % (self.job.id, step_index))
                step.run(args)
                job_log.debug("Job %d step %d successful" % (self.job.id, step_index))

                result.state = 'success'
            except AgentException, e:
                job_log.error("Job %d step %d encountered an agent error" % (self.job.id, step_index))
                self._job_scheduler.complete_job(self.job, errored = True)

                result.backtrace = e.agent_backtrace
                # Don't bother storing the backtrace to invoke_agent, the interesting part
                # is the backtrace inside the AgentException
                result.state = 'failed'
                result.save()

                return None

            except Exception:
                job_log.error("Job %d step %d encountered an error" % (self.job.id, step_index))
                exc_info = sys.exc_info()
                backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
                job_log.error(backtrace)
                self._job_scheduler.complete_job(self.job, errored = True)

                result.backtrace = backtrace
                result.state = 'failed'
                result.save()

                return None
            finally:
                result.save()

            finish_step = step_index
            step_index += 1

        # For StateChangeJobs, set update the state of the affected object
        if isinstance(self.job, StateChangeJob):
            obj = self.job.get_stateful_object()
            obj = obj.__class__._base_manager.get(pk = obj.pk)
            new_state = self.job.state_transition[2]
            obj.set_state(new_state, intentional = True)
            job_log.info("Job %d: StateChangeJob complete, setting state %s on %s" % (self.job.pk, new_state, obj))

        # Freshen cached information about anything that this job held a writelock on
        locks = json.loads(self.job.locks_json)
        for lock in locks:
            if lock['write']:
                lock = StateLock.from_dict(self.job, lock)
                if isinstance(lock.locked_item, DeletableStatefulObject) and not lock.locked_item.not_deleted:
                    ObjectCache.purge(lock.locked_item.__class__, lambda o: o.id == lock.locked_item.id)
                else:
                    ObjectCache.update(lock.locked_item)

        job_log.info("Job %d finished %d steps successfully" % (self.job.id, finish_step + 1))

        with transaction.commit_manually():
            transaction.commit()

        self._job_scheduler.complete_job(self.job, errored = False)

        return None


class JobScheduler(object):
    def __init__(self):
        self._lock = threading.RLock()
        """Globally serialize all scheduling operations: within a given cluster, they all potentially
        interfere with one another.  In the future, if this class were handling multiple isolated
        clusters then they could take a lock each and run in parallel

        """

        self._lock_cache = LockCache()

    @transaction.commit_on_success
    def _run_next(self):
        runnable_jobs = Job.get_ready_jobs()

        job_log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (
            len(runnable_jobs),
            Job.objects.filter(state = 'pending').count(),
            Job.objects.filter(state = 'tasked').count()))

        dep_cache = DepCache()
        for job in runnable_jobs:
            self._start_job(job, dep_cache)

    def _start_job(self, job, dep_cache):
        job_log.info("Job %d: Job.run %s" % (job.id, job.description()))
        # We've reached the head of the queue, all I need to check now
        # is - are this Job's immediate dependencies satisfied?  And are any deps
        # for a statefulobject's new state satisfied?  If so, continue.  If not, cancel.

        try:
            deps_satisfied = job._deps_satisfied(dep_cache)
        except Exception:
            # Catchall exception handler to ensure progression even if Job
            # subclasses have bugs in their get_deps etc.
            job_log.error("Job %s: exception in dependency check: %s" % (job.id,
                                                                         '\n'.join(traceback.format_exception(*(sys.exc_info())))))
            self.complete_job(job, cancelled = True)
            return

        if not deps_satisfied:
            job_log.warning("Job %d: cancelling because of failed dependency" % job.id)
            self.complete_job(job, cancelled = True)
            # TODO: tell someone WHICH dependency
            return

        job.state = 'tasked'
        job.save()

        self._spawn_job(job)

    def _spawn_job(self, job):
        RunJobThread(self, job).start()

    def _complete_job(self, job, errored, cancelled):
        job_log.info("Job %s completing (errored=%s, cancelled=%s)" %
                     (job.id, errored, cancelled))
        job.state = 'complete'
        job.errored = errored
        job.cancelled = cancelled
        job.save()

        job = job.downcast()

        if job.locks_json:
            try:
                command = Command.objects.filter(jobs = job, complete = False)[0]
            except IndexError:
                job_log.warning("Job %s: No incomplete command while completing" % job.pk)
                command = None

            locks = json.loads(job.locks_json)

            # Update _lock_cache to remove the completed job's locks
            self._lock_cache.remove_job(job)

            # Check for completion callbacks on anything this job held a writelock on
            for lock in locks:
                if lock['write']:
                    lock = StateLock.from_dict(job, lock)
                    job_log.debug("Job %s completing, held writelock on %s" % (job.pk, lock.locked_item))
                    try:
                        self._completion_hooks(lock.locked_item, command)
                    except Exception:
                        job_log.error("Error in completion hooks: %s" % '\n'.join(traceback.format_exception(*(sys.exc_info()))))
        else:
            job_log.debug("Job %s completing, held no locks" % job.pk)

        for command in Command.objects.filter(jobs = job):
            command.check_completion()

    def _completion_hooks(self, changed_item, command = None):
        """
        :param command: If set, any created jobs are added
        to this command object.
        """
        if hasattr(changed_item, 'content_type'):
            changed_item = changed_item.downcast()

        job_log.debug("_completion_hooks command %s, %s (%s) state=%s" % (command, changed_item, changed_item.__class__, changed_item.state))

        def running_or_failed(klass, **kwargs):
            """Look for jobs of the same type with the same params, either incomplete (don't start the job because
            one is already pending) or complete in the same command (don't start the job because we already tried and failed)"""
            if command:
                count = klass.objects.filter(~Q(state = 'complete') | Q(command = command), **kwargs).count()
            else:
                count = klass.objects.filter(~Q(state = 'complete'), **kwargs).count()

            return bool(count)

        if isinstance(changed_item, FilesystemMember):
            fs = changed_item.filesystem
            members = list(ManagedMdt.objects.filter(filesystem = fs)) + list(ManagedOst.objects.filter(filesystem = fs))
            states = set([t.state for t in members])
            now = datetime.datetime.utcnow().replace(tzinfo = tz.tzutc())

            if not fs.state == 'available' and changed_item.state in ['mounted', 'removed'] and states == set(['mounted']):
                job_log.debug('branched')
                self._notify_state(ContentType.objects.get_for_model(fs).natural_key(), fs.id, now, 'available', ['stopped', 'unavailable'])
            if changed_item.state == 'unmounted' and fs.state != 'stopped' and states == set(['unmounted']):
                self._notify_state(ContentType.objects.get_for_model(fs).natural_key(), fs.id, now, 'stopped', ['stopped', 'unavailable'])
            if changed_item.state == 'unmounted' and fs.state == 'available' and states != set(['mounted']):
                self._notify_state(ContentType.objects.get_for_model(fs).natural_key(), fs.id, now, 'unavailable', ['available'])

        if isinstance(changed_item, ManagedHost):
            if changed_item.state == 'lnet_up' and changed_item.lnetconfiguration.state != 'nids_known':
                if not running_or_failed(ConfigureLNetJob, lnet_configuration = changed_item.lnetconfiguration):
                    job = ConfigureLNetJob(lnet_configuration = changed_item.lnetconfiguration, old_state = 'nids_unknown')
                    if not command:
                        command = Command.objects.create(message = "Configuring LNet on %s" % changed_item)
                    ModificationOperation(self._lock_cache).add_jobs([job], command)
                else:
                    job_log.debug('running_or_failed')

            if changed_item.state == 'configured':
                if not running_or_failed(GetLNetStateJob, host = changed_item):
                    job = GetLNetStateJob(host = changed_item)
                    if not command:
                        command = Command.objects.create(message = "Getting LNet state for %s" % changed_item)
                    ModificationOperation(self._lock_cache).add_jobs([job], command)

        if isinstance(changed_item, ManagedTarget):
            if isinstance(changed_item, FilesystemMember):
                mgs = changed_item.filesystem.mgs
            else:
                mgs = changed_item

            if mgs.conf_param_version != mgs.conf_param_version_applied:
                if not running_or_failed(ApplyConfParams, mgs = mgs):
                    job = ApplyConfParams(mgs = mgs)
                    if DepCache().get(job).satisfied():
                        if not command:
                            command = Command.objects.create(message = "Updating configuration parameters on %s" % mgs)
                        ModificationOperation(self._lock_cache).add_jobs([job], command)

    @transaction.commit_on_success
    def complete_job(self, job, errored = False, cancelled = False):
        with self._lock:
            ObjectCache.clear()

            self._complete_job(job, errored, cancelled)
            self._run_next()

    def set_state(self, object_ids, message, run):
        with self._lock:
            ObjectCache.clear()
            with transaction.commit_on_success():
                rc = ModificationOperation(self._lock_cache).command_set_state(object_ids, message)
            if run:
                self._run_next()
        return rc

    def _notify_state(self, content_type, object_id, notification_time, new_state, from_states):
        # Get the StatefulObject
        from django.contrib.contenttypes.models import ContentType
        model_klass = ContentType.objects.get_by_natural_key(*content_type).model_class()
        instance = model_klass.objects.get(pk = object_id).downcast()

        # Assert its class
        from chroma_core.models import StatefulObject
        assert(isinstance(instance, StatefulObject))

        # If a state update is needed/possible
        if instance.state in from_states and instance.state != new_state:
            # Check that no incomplete jobs hold a lock on this object
            if not len(self._lock_cache.get_by_locked_item(instance)):
                modified_at = instance.state_modified_at
                modified_at = modified_at.replace(tzinfo = tz.tzutc())

                if notification_time > modified_at:
                    # No jobs lock this object, go ahead and update its state
                    job_log.info("notify_state: Updating state of item %s (%s) from %s to %s" % (instance.id, instance, instance.state, new_state))
                    instance.set_state(new_state)
                    ObjectCache.update(instance)

                    # FIXME: should check the new state against reverse dependencies
                    # and apply any fix_states
                    self._completion_hooks(instance)
                else:
                    job_log.info("notify_state: Dropping update of %s (%s) %s->%s because it has been updated since" % (instance.id, instance, instance.state, new_state))
                    pass
            else:
                job_log.info("notify_state: Dropping update to %s because of locks" % instance)
                for lock in self._lock_cache.get_by_locked_item(instance):
                    job_log.info("  %s" % lock)
        else:
            job_log.info("notify_state: Dropping update to %s because its state is %s" % (instance, instance.state))

    @transaction.commit_on_success
    def notify_state(self, content_type, object_id, time_serialized, new_state, from_states):
        with self._lock:
            ObjectCache.clear()

            notification_time = dateutil.parser.parse(time_serialized)
            self._notify_state(content_type, object_id, notification_time, new_state, from_states)

            self._run_next()

    @transaction.commit_on_success
    def run_jobs(self, job_dicts, message):
        with self._lock:
            ObjectCache.clear()

            result = ModificationOperation(self._lock_cache).command_run_jobs(job_dicts, message)
            self._run_next()
        return result

    @transaction.commit_on_success
    def cancel_job(self, job_id):
        Job.objects.filter(pk = job_id).update(state = 'cancelled')
        # FIXME: implement
        raise NotImplementedError()
