#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import socket
import subprocess
import threading
import sys
import traceback
import urlparse

import os
import operator
import itertools
from collections import defaultdict
import Queue
import dateutil.parser
from copy import deepcopy
from paramiko import SSHException, AuthenticationException

from chroma_core.models.registration_token import RegistrationToken
from chroma_core.services.http_agent.crypto import Crypto


from django.contrib.contenttypes.models import ContentType
from django.db import transaction, DEFAULT_DB_ALIAS
from django.db.models import Q
import django.utils.timezone

from chroma_core.lib.cache import ObjectCache
from chroma_core.models import Command, StateLock, ConfigureLNetJob, ManagedHost, ManagedMdt, FilesystemMember, GetLNetStateJob, ManagedTarget, ApplyConfParams, \
    ManagedOst, Job, DeletableStatefulObject, StepResult, ManagedMgs, ManagedFilesystem, LNetConfiguration, ManagedTargetMount, VolumeNode, ConfigureHostFencingJob
from chroma_core.services.job_scheduler.dep_cache import DepCache
from chroma_core.services.job_scheduler.lock_cache import LockCache
from chroma_core.services.job_scheduler.command_plan import CommandPlan
from chroma_core.services.job_scheduler.agent_rpc import AgentException
from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
from chroma_core.services.log import log_register
import chroma_core.lib.conf_param
import settings


log = log_register(__name__.split('.')[-1])


class NotificationBuffer(object):
    """
    Provides a simple buffer for notifications which would otherwise be
    dropped due to lock contention on the notified item.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._notifications = defaultdict(Queue.Queue)

    def add_notification_for_key(self, key, notification):
        with self._lock:
            self._notifications[key].put(notification)

    @property
    def notification_keys(self):
        with self._lock:
            return self._notifications.keys()

    def clear_notifications_for_key(self, key):
        with self._lock:
            del(self._notifications[key])

    def drain_notifications_for_key(self, key):
        notifications = []
        with self._lock:
            while not self._notifications[key].empty():
                notifications.append(self._notifications[key].get())
            del(self._notifications[key])
        return notifications


class SimpleConnectionQuota(object):
    """
    This class provides a way to limit the total number of DB connections
    used by a population of threads.

    It is *not* a pool: the connections are destroyed and created every time.

    It's for when threads need to briefly dip into a period of database access
    before giving it up again.
    """

    def __init__(self, max_connections):
        self._semaphore = threading.Semaphore(max_connections)
        self.db_alias = DEFAULT_DB_ALIAS
        self.database = django.db.connections.databases[self.db_alias]

    def acquire(self):
        self._semaphore.acquire()
        if django.db.connection.connection == DISABLED_CONNECTION:
            django.db.connection.connection = None
        #connection = load_backend(self.database['ENGINE']).DatabaseWrapper(self.database, self.db_alias)
        #return connection

    def release(self, connection):
        # Close the connection if present, and hand back our token
        if django.db.connection.connection:
            _disable_database()

        self._semaphore.release()


class DisabledConnection(object):
    def __getattr__(self, item):
        raise RuntimeError("Attempted to use database from a step which does not have database=True")

DISABLED_CONNECTION = DisabledConnection()


def _disable_database():
    if django.db.connection.connection is not None and django.db.connection.connection != DISABLED_CONNECTION:
        django.db.connection.close()
    django.db.connection.connection = DISABLED_CONNECTION


class JobProgress(threading.Thread, Queue.Queue):
    """
    A thread and a queue for handling progress/completion information
    from RunJobThread
    """

    def __init__(self, job_scheduler):
        threading.Thread.__init__(self)
        Queue.Queue.__init__(self)

        self._job_scheduler = job_scheduler

        self._stopping = threading.Event()
        self._job_to_result = {}

    def run(self):
        while not self._stopping.is_set():
            try:
                self._handle(self.get(block = True, timeout = 1))
            except Queue.Empty:
                pass

        for msg in self.queue:
            self._handle(msg)

    def _handle(self, msg):
        fn = getattr(self, "_%s" % msg[0])
        # Commit after each message to ensure the next message handler
        # doesn't see a stale transaction
        with transaction.commit_on_success():
            fn(*msg[1], **msg[2])

    def stop(self):
        self._stopping.set()

    def complete_job(self, job_id, errored):
        if django.db.connection.connection and django.db.connection.connection != DISABLED_CONNECTION:
            log.info("Job %d: open DB connection during completion" % job_id)
            # Ensure that any changes made by this thread are visible to other threads before
            # we ask job_scheduler to advance
            with transaction.commit_manually():
                transaction.commit()

        self.put(('complete_job', (job_id, errored), {}))

    def __getattr__(self, name):
        if not name.startswith('_'):
            # Throw an exception if there isn't an underscored method to
            # handle this
            self.__getattr__("_%s" % name)
            return lambda *args, **kwargs: self.put(deepcopy((name, args, kwargs)))

    def _complete_job(self, job_id, errored):
        self._job_scheduler.complete_job(job_id, errored=errored)

    def _advance(self):
        self._job_scheduler.advance()

    def _start_step(self, job_id, **kwargs):
        with transaction.commit_on_success():
            result = StepResult(job_id=job_id, **kwargs)
            result.save()
        self._job_to_result[job_id] = result

    def _log(self, job_id, log_string):
        result = self._job_to_result[job_id]
        with transaction.commit_on_success():
            result.log += log_string
            result.save()

    def _console(self, job_id, log_string):
        result = self._job_to_result[job_id]
        with transaction.commit_on_success():
            result.console += log_string
            result.save()

    def _step_failure(self, job_id, backtrace):
        result = self._job_to_result[job_id]
        with transaction.commit_on_success():
            result.state = 'failed'
            result.backtrace = backtrace
            result.save()

    def _step_success(self, job_id):
        result = self._job_to_result[job_id]
        with transaction.commit_on_success():
            result.state = 'success'
            result.save()


class RunJobThread(threading.Thread):
    CANCEL_TIMEOUT = 30

    def __init__(self, job_progress, connection_quota, job, steps):
        super(RunJobThread, self).__init__()
        self.job = job
        self._job_progress = job_progress
        self._connection_quota = connection_quota
        self._cancel = threading.Event()
        self._complete = threading.Event()
        self.steps = steps

    def cancel(self):
        log.info("Job %s: cancelling" % self.job.id)
        self._cancel.set()
        log.info("Job %s: waiting %ss for run to complete" % (self.job.id, self.CANCEL_TIMEOUT))

    def cancel_complete(self):
        self._complete.wait(self.CANCEL_TIMEOUT)
        if self._complete.is_set():
            log.info("Job %s: cancel completed" % self.job.id)
        else:
            # HYD-1485: Get a mechanism to interject when the thread is blocked on an agent call
            log.error("Job %s: cancel timed out, will continue as zombie thread!" % self.job.id)

    def run(self):
        if django.db.connection.connection:
            log.error("RunJobThread started with a DB connection!")

        try:
            self._run()
            self._complete.set()
        except Exception:
            log.critical("Unhandled exception in RunJobThread: %s" % traceback.format_exc())
            # Better to die clean than live on dirty (an unhandled exception
            # could mean that we will leave Command/Job/StepResult objects in
            # a bad/never-completing state).
            os._exit(-1)

        if django.db.connection.connection and django.db.connection.connection != DISABLED_CONNECTION:
            django.db.connection.close()

    def _run(self):
        log.info("Job %d: %s.run" % (self.job.id, self.__class__.__name__))

        step_index = 0
        finish_step = -1
        while step_index < len(self.steps) and not self._cancel.is_set():
            klass, args = self.steps[step_index]
            self._job_progress.start_step(
                self.job.id,
                step_klass=klass,
                args=args,
                step_index=step_index,
                step_count=len(self.steps))

            step = klass(self.job,
                         args,
                         lambda l: self._job_progress.log(self.job.id, l),
                         lambda c: self._job_progress.console(self.job.id, c),
                         self._cancel)

            try:
                if step.database:
                    # Get a token entitling code running in this thread
                    # to open a database connection when it chooses to
                    self._connection_quota.acquire()
                else:
                    _disable_database()

                log.debug("Job %d running step %d" % (self.job.id, step_index))
                step.run(args)
                log.debug("Job %d step %d successful" % (self.job.id, step_index))

                self._job_progress.step_success(self.job.id)
            except AgentException, e:
                log.error("Job %d step %d encountered an agent error: %s" % (self.job.id, step_index, e.backtrace))

                # Don't bother storing the backtrace to invoke_agent, the interesting part
                # is the backtrace inside the AgentException
                self._job_progress.step_failure(self.job.id, e.backtrace)
                self._job_progress.complete_job(self.job.id, errored = True)
                return
            except Exception:
                backtrace = traceback.format_exc()
                log.error("Job %d step %d encountered an error: %s" % (self.job.id, step_index, backtrace))

                self._job_progress.step_failure(self.job.id, backtrace)
                self._job_progress.complete_job(self.job.id, errored = True)
                return
            finally:
                if step.database:
                    log.debug("Job %d releasing database connection" % self.job.id)
                    self._connection_quota.release(django.db.connection.connection)

            finish_step = step_index
            step_index += 1

        if self._cancel.is_set():
            return

        log.info("Job %d finished %d steps successfully" % (self.job.id, finish_step + 1))

        self._job_progress.complete_job(self.job.id, errored = False)


class JobCollection(object):
    def __init__(self):
        self.flush()

    def flush(self):
        self._state_jobs = {
            'pending': {},
            'tasked': {},
            'complete': {}
        }
        self._jobs = {}
        self._commands = {}

        self._command_to_jobs = defaultdict(set)
        self._job_to_commands = defaultdict(set)

    def add(self, job):
        self._jobs[job.id] = job
        self._state_jobs[job.state][job.id] = job

    def add_command(self, command, jobs):
        """Add command if it doesn't already exist, and ensure that all
        of `jobs` are associated with it

        """
        for job in jobs:
            self.add(job)
        self._commands[command.id] = command
        self._command_to_jobs[command.id] |= set([j.id for j in jobs])
        for job in jobs:
            self._job_to_commands[job.id].add(command.id)

    def get(self, job_id):
        return self._jobs[job_id]

    def update(self, job, new_state, **kwargs):
        initial_state = job.state

        Job.objects.filter(id = job.id).update(state = new_state, **kwargs)
        job.state = new_state
        for attr, val in kwargs.items():
            setattr(job, attr, val)

        try:
            del self._state_jobs[initial_state][job.id]
        except KeyError:
            log.warning("Cancelling uncached Job %s" % job.id)
        else:
            self._state_jobs[job.state][job.id] = job

    def update_commands(self, job):
        """
        Update any commands which relate to this job (complete the command if all its jobs are complete)
        """
        if job.state == 'complete':
            for command_id in self._job_to_commands[job.id]:
                jobs = [self._jobs[job_id] for job_id in self._command_to_jobs[command_id]]
                if set([j.state for j in jobs]) == set(['complete']) or len(jobs) == 0:
                    # Mark the command as complete
                    errored = True in [j.errored for j in jobs]
                    cancelled = True in [j.cancelled for j in jobs]
                    log.debug("Completing command %s (%s, %s) as a result of completing job %s" % (command_id, errored, cancelled, job.id))
                    if errored or cancelled:
                        for job in jobs:
                            log.debug("Command %s job %s: %s %s" % (command_id, job.id, job.errored, job.cancelled))

                    self._commands[command_id].errored = errored
                    self._commands[command_id].cancelled = cancelled
                    self._commands[command_id].complete = True
                    Command.objects.filter(pk = command_id).update(errored = errored, cancelled = cancelled, complete = True)

    def update_many(self, jobs, new_state):
        for job in jobs:
            del self._state_jobs[job.state][job.id]
            job.state = new_state
            self._state_jobs[job.state][job.id] = job

        Job.objects.filter(id__in = [j.id for j in jobs]).update(state = new_state)

    @property
    def ready_jobs(self):
        result = []
        for job in self._state_jobs['pending'].values():
            wait_for_ids = json.loads(job.wait_for_json)
            complete_job_ids = [j.id for j in self._state_jobs['complete'].values()]
            if not set(wait_for_ids) - set(complete_job_ids):
                result.append(job)

        if len(result) == 0 and len(self.pending_jobs) == 0 and len(self.tasked_jobs) == 0:
            # A quiescent state, flush the collection (avoid building up an indefinitely
            # large collection of complete jobs)
            log.debug("%s.flush" % (self.__class__.__name__))
            self.flush()

        return result

    @property
    def pending_jobs(self):
        return self._state_jobs['pending'].values()

    @property
    def tasked_jobs(self):
        return self._state_jobs['tasked'].values()


class JobScheduler(object):
    """A single instance of this class is created within the `job_scheduler` service.

    It is on the receiving end of RPCs (JobSchedulerRpc) and also is called
    by the handler for NotificationQueue


    """

    MAX_STEP_DB_CONNECTIONS = 10

    def __init__(self):
        self._lock = threading.RLock()
        """Globally serialize all scheduling operations: within a given cluster, they all potentially
        interfere with one another.  In the future, if this class were handling multiple isolated
        clusters then they could take a lock each and run in parallel

        """

        self._lock_cache = LockCache()
        self._job_collection = JobCollection()
        self._notification_buffer = NotificationBuffer()

        self._db_quota = SimpleConnectionQuota(self.MAX_STEP_DB_CONNECTIONS)
        self._run_threads = {}  # Map of job ID to RunJobThread

        self.progress = JobProgress(self)

    def join_run_threads(self):
        for job_id, thread in self._run_threads.items():
            log.info("Joining thread for job %s" % job_id)
            thread.join()

    def _run_next(self):
        ready_jobs = self._job_collection.ready_jobs

        log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (
            len(ready_jobs),
            len(self._job_collection.pending_jobs),
            len(self._job_collection.tasked_jobs)))

        dep_cache = DepCache()
        ok_jobs, cancel_jobs = self._check_jobs(ready_jobs, dep_cache)

        for job in cancel_jobs:
            self._complete_job(job, False, True)

        self._job_collection.update_many(ok_jobs, 'tasked')
        for job in ok_jobs:
            self._spawn_job(job)

        if cancel_jobs:
            # Cancellations may have made some jobs ready, run me again
            self._run_next()

    def _check_jobs(self, jobs, dep_cache):
        """Return the list of jobs which pass their checks"""
        ok_jobs = []
        cancel_jobs = []

        for job in jobs:
            try:
                deps_satisfied = job._deps_satisfied(dep_cache)
            except Exception:
                # Catchall exception handler to ensure progression even if Job
                # subclasses have bugs in their get_deps etc.
                log.error("Job %s: exception in dependency check: %s" % (job.id,
                                                                         '\n'.join(traceback.format_exception(*(sys.exc_info())))))
                cancel_jobs.append(job)
            else:
                if not deps_satisfied:
                    log.warning("Job %d: cancelling because of failed dependency" % job.id)
                    cancel_jobs.append(job)
                    # TODO: tell someone WHICH dependency
                else:
                    try:
                        job.steps = job.get_steps()
                    except Exception:
                        log.error("Job %d: exception in get_steps: %s" % (job.id, traceback.format_exc()))
                        cancel_jobs.append(job)
                    else:
                        ok_jobs.append(job)

        return ok_jobs, cancel_jobs

    def _spawn_job(self, job):
        # NB job.steps was decorated onto job in _check_jobs, because that's where we need to handle any exceptions from it
        # NB we call get_steps in here rather than RunJobThread so that steps can be composed using DB operations
        # without having a database connection for each RunJobThread

        if job.steps:
            thread = RunJobThread(self.progress, self._db_quota, job, job.steps)
            assert not job.id in self._run_threads
            self._run_threads[job.id] = thread

            # Make sure the thread doesn't spawn a new DB connection by default
            django.db.connection.close()

            thread.start()
            log.debug('_spawn_job: %s threads in flight' % len(self._run_threads))
        else:
            log.debug('_spawn_job: No steps for %s, completing' % job.pk)
            # No steps: skip straight to completion
            self.progress.complete_job(job.id, False)

    def _complete_job(self, job, errored, cancelled):
        try:
            del self._run_threads[job.id]
        except KeyError:
            pass

        log.debug('_complete_job: %s threads in flight' % len(self._run_threads))

        log.info("Job %s completing (errored=%s, cancelled=%s)" %
                 (job.id, errored, cancelled))

        try:
            command = Command.objects.filter(jobs = job, complete = False)[0]
        except IndexError:
            log.warning("Job %s: No incomplete command while completing" % job.pk)
            command = None

        self._job_collection.update(job, 'complete', errored = errored, cancelled = cancelled)

        locks = json.loads(job.locks_json)

        # Update _lock_cache to remove the completed job's locks
        self._lock_cache.remove_job(job)

        # Check for completion callbacks on anything this job held a writelock on
        for lock in locks:
            if lock['write']:
                lock = StateLock.from_dict(job, lock)
                log.debug("Job %s completing, held writelock on %s" % (job.pk, lock.locked_item))
                try:
                    self._completion_hooks(lock.locked_item, command)
                except Exception:
                    log.error("Error in completion hooks: %s" % '\n'.join(traceback.format_exception(*(sys.exc_info()))))

        # Do this last so that the state of the command reflects both the completion
        # of this job and any new jobs added by completion hooks
        self._job_collection.update_commands(job)

    def _completion_hooks(self, changed_item, command = None, updated_attrs = []):
        """
        :param command: If set, any created jobs are added
        to this command object.
        """
        log.debug("_completion_hooks command %s, %s (%s) state=%s" % (
            None if command is None else command.id, changed_item, changed_item.__class__, changed_item.state))

        def running_or_failed(klass, **kwargs):
            """Look for jobs of the same type with the same params, either incomplete (don't start the job because
            one is already pending) or complete in the same command (don't start the job because we already tried and failed)"""
            if command:
                count = klass.objects.filter(~Q(state = 'complete') | Q(command = command), **kwargs).count()
            else:
                count = klass.objects.filter(~Q(state = 'complete'), **kwargs).count()

            return bool(count)

        if isinstance(changed_item, ManagedTarget):
            if issubclass(changed_item.downcast_class, FilesystemMember):
                affected_filesystems = [changed_item.downcast().filesystem]
            else:
                affected_filesystems = changed_item.downcast().managedfilesystem_set.all()

            for filesystem in affected_filesystems:
                members = filesystem.get_targets()
                states = set([t.state for t in members])
                now = django.utils.timezone.now()

                if not filesystem.state == 'available' and changed_item.state in ['mounted', 'removed'] and states == set(['mounted']):
                    self._notify(ContentType.objects.get_for_model(filesystem).natural_key(), filesystem.id, now, {'state': 'available'}, ['stopped', 'unavailable'])
                if changed_item.state == 'unmounted' and filesystem.state != 'stopped' and states == set(['unmounted']):
                    self._notify(ContentType.objects.get_for_model(filesystem).natural_key(), filesystem.id, now, {'state': 'stopped'}, ['stopped', 'unavailable'])
                if changed_item.state == 'unmounted' and filesystem.state == 'available' and states != set(['mounted']):
                    self._notify(ContentType.objects.get_for_model(filesystem).natural_key(), filesystem.id, now, {'state': 'unavailable'}, ['available'])

        if isinstance(changed_item, ManagedHost):
            if changed_item.state == 'lnet_up' and changed_item.lnetconfiguration.state != 'nids_known':
                if not running_or_failed(ConfigureLNetJob, lnet_configuration = changed_item.lnetconfiguration):
                    job = ConfigureLNetJob(lnet_configuration = changed_item.lnetconfiguration, old_state = 'nids_unknown')
                    if not command:
                        command = Command.objects.create(message = "Configuring LNet on %s" % changed_item)
                    CommandPlan(self._lock_cache, self._job_collection).add_jobs([job], command)
                else:
                    log.debug('running_or_failed')

            if changed_item.state == 'configured':
                if not running_or_failed(GetLNetStateJob, host = changed_item):
                    job = GetLNetStateJob(host = changed_item)
                    if not command:
                        command = Command.objects.create(message = "Getting LNet state for %s" % changed_item)
                    CommandPlan(self._lock_cache, self._job_collection).add_jobs([job], command)

            if 'ha_cluster_peers' in updated_attrs:
                AgentDaemonRpcInterface().rebalance_host_volumes(changed_item.id)

            if changed_item.needs_fence_reconfiguration:
                job = ConfigureHostFencingJob(host = changed_item)
                command = Command.objects.create(message = "Configuring host fencing")
                CommandPlan(self._lock_cache, self._job_collection).add_jobs([job], command)

        if isinstance(changed_item, ManagedTarget):
            # See if any MGS conf params need applying
            if issubclass(changed_item.downcast_class, FilesystemMember):
                mgs = changed_item.downcast().filesystem.mgs
            else:
                mgs = changed_item.downcast()

            if mgs.conf_param_version != mgs.conf_param_version_applied:
                if not running_or_failed(ApplyConfParams, mgs = mgs.managedtarget_ptr):
                    job = ApplyConfParams(mgs = mgs.managedtarget_ptr)
                    if DepCache().get(job).satisfied():
                        if not command:
                            command = Command.objects.create(message = "Updating configuration parameters on %s" % mgs)
                        CommandPlan(self._lock_cache, self._job_collection).add_jobs([job], command)

            # Update TargetFailoverAlert from .active_mount
            from chroma_core.models import TargetFailoverAlert
            failed_over = changed_item.active_mount is not None and changed_item.active_mount != changed_item.managedtargetmount_set.get(primary = True)
            TargetFailoverAlert.notify(changed_item, failed_over)

    def _drain_notification_buffer(self):
        # Give any buffered notifications a chance to drain out
        for buffer_key in self._notification_buffer.notification_keys:
            content_type, object_id = buffer_key
            model_klass = ContentType.objects.get_by_natural_key(*content_type).model_class()
            try:
                instance = model_klass.objects.get(pk = object_id).downcast()
            except model_klass.DoesNotExist:
                log.warning("_drain_notification_buffer: Dropping buffered notifications for not-found object %s/%s" % buffer_key)
                self._notification_buffer.clear_notifications_for_key(buffer_key)
                continue

            # Try again later if the instance is still locked
            if self._lock_cache.get_by_locked_item(instance):
                continue

            notifications = self._notification_buffer.drain_notifications_for_key(buffer_key)
            log.info("Replaying %d buffered notifications for %s-%s" % (len(notifications), model_klass.__name__, instance.pk))
            for notification in notifications:
                log.debug("Replaying buffered notification: %s" % (notification,))
                self._notify(*notification)

    def set_state(self, object_ids, message, run):
        with self._lock:
            with transaction.commit_on_success():
                command = CommandPlan(self._lock_cache, self._job_collection).command_set_state(object_ids, message)
            if run:
                self.progress.advance()
        return command.id

    @transaction.commit_on_success
    def advance(self):
        with self._lock:
            self._run_next()

    def _notify(self, content_type, object_id, notification_time, update_attrs, from_states):
        # Get the StatefulObject
        model_klass = ContentType.objects.get_by_natural_key(*content_type).model_class()
        try:
            instance = ObjectCache.get_by_id(model_klass, object_id)
        except model_klass.DoesNotExist:
            log.warning("_notify: Dropping update for not-found object %s/%s" % (content_type, object_id))
            return

        # Drop if it's not in an allowed state
        if from_states and not instance.state in from_states:
            log.info("_notify: Dropping update to %s because %s is not in %s" % (instance, instance.state, from_states))
            return

        # Drop state-modifying updates if outdated
        modified_at = instance.state_modified_at
        if 'state' in update_attrs and notification_time <= modified_at:
            log.info("notify: Dropping update of %s (%s) because it has been updated since" % (instance.id, instance))
            return

        # Buffer updates on locked instances, except for state changes. By the
        # time a buffered state change notification would be replayed, the
        # state change would probably not make any sense.
        if self._lock_cache.get_by_locked_item(instance):
            if 'state' in update_attrs:
                return

            log.info("_notify: Buffering update to %s because of locks" % instance)
            for lock in self._lock_cache.get_by_locked_item(instance):
                log.info("  %s" % lock)

            buffer_key = (tuple(content_type), object_id)
            notification = (content_type, object_id, notification_time, update_attrs, from_states)
            self._notification_buffer.add_notification_for_key(buffer_key, notification)

            return

        for attr, value in update_attrs.items():
            old_value = getattr(instance, attr)
            if old_value == value:
                log.info("_notify: Dropping %s.%s = %s because it is already set" % (instance, attr, value))
                continue

            log.info("_notify: Updating .%s of item %s (%s) from %s to %s" % (attr, instance.id, instance, old_value, value))
            if attr == 'state':
                # If setting the special 'state' attribute then maybe schedule some jobs
                instance.set_state(value)
            else:
                # If setting a normal attribute just write it straight away
                setattr(instance, attr, value)
                instance.save()
                log.info("_notify: Set %s=%s on %s (%s-%s) and saved" % (attr, value, instance, model_klass.__name__, instance.id))

        instance.save()

        # Foreign keys: annoyingly, if foo_id was 7, and we assign it to 8, then .foo will still be
        # the '7' instance, even after a save().  To be safe against any such strangeness, pull a
        # fresh instance of everything we update (this is safe because earlier we checked that nothing is
        # locking this object.
        instance = ObjectCache.update(instance)

        # FIXME: should check the new state against reverse dependencies
        # and apply any fix_states
        self._completion_hooks(instance, updated_attrs = update_attrs.keys())

    @transaction.commit_on_success
    def notify(self, content_type, object_id, time_serialized, update_attrs, from_states):
        with self._lock:
            notification_time = dateutil.parser.parse(time_serialized)
            self._notify(content_type, object_id, notification_time, update_attrs, from_states)

            self._run_next()

    @transaction.commit_on_success
    def run_jobs(self, job_dicts, message):
        with self._lock:
            result = CommandPlan(self._lock_cache, self._job_collection).command_run_jobs(job_dicts, message)
            self.progress.advance()
            return result

    @transaction.commit_on_success
    def cancel_job(self, job_id):
        cancelled_thread = None

        with self._lock:
            try:
                job = self._job_collection.get(job_id)
            except KeyError:
                # Job has been cleaned out of collection, therefore is complete
                # However, to avoid being too trusting, let's retrieve it and
                # let the following check for completeness happen
                job = Job.objects.get(pk = job_id)

            log.info("cancel_job: Cancelling job %s (%s)" % (job.id, job.state))
            if job.state == 'complete':
                return
            elif job.state == 'tasked':
                try:
                    cancelled_thread = self._run_threads[job_id]
                    cancelled_thread.cancel()
                except KeyError:
                    pass
                self._job_collection.update(job, 'complete', cancelled = True)
                self._job_collection.update_commands(job)
            elif job.state == 'pending':
                self._job_collection.update(job, 'complete', cancelled = True)
                self._job_collection.update_commands(job)

        # Drop self._lock while the thread completes - it will need
        # this lock to send back its completion
        if cancelled_thread is not None:
            cancelled_thread.cancel_complete()
        else:
            # So that anything waiting on this job can be cancelled too
            self.progress.advance()

    def complete_job(self, job_id, errored = False, cancelled = False):
        # TODO: document the rules here: jobs may only modify objects that they
        # have taken out a writelock on, and they may only modify instances obtained
        # via ObjectCache, or via their stateful_object attribute.  Jobs may not
        # modify objects via .update() calls, all changes must be done on loaded instances.
        # They do not have to .save() their stateful_object, but they do have to .save()
        # any other objects that they modify (having obtained their from ObjectCache and
        # held a writelock on them)

        job = self._job_collection.get(job_id)
        with self._lock:
            with transaction.commit_on_success():
                if not errored and not cancelled:
                    try:
                        job.on_success()
                    except Exception:
                        log.error("Error in Job %s on_success:%s" % (job.id, traceback.format_exc()))
                        errored = True

                log.info("Job %d: complete_job: Updating cache" % job.pk)
                # Freshen cached information about anything that this job held a writelock on
                for lock in self._lock_cache.get_by_job(job):
                    if lock.write:
                        if hasattr(lock.locked_item, 'not_deleted'):
                            log.info("Job %d: locked_item %s %s %s %s" % (
                                job.id,
                                id(lock.locked_item),
                                lock.locked_item.__class__,
                                isinstance(lock.locked_item, DeletableStatefulObject),
                                lock.locked_item.not_deleted
                            ))
                        if hasattr(lock.locked_item, 'not_deleted') and lock.locked_item.not_deleted is None:
                            log.debug("Job %d: purging %s/%s" %
                                     (job.id, lock.locked_item.__class__, lock.locked_item.id))
                            ObjectCache.purge(lock.locked_item.__class__, lambda o: o.id == lock.locked_item.id)
                        else:
                            log.debug("Job %d: updating write-locked %s/%s" %
                                     (job.id, lock.locked_item.__class__, lock.locked_item.id))
                            ObjectCache.update(lock.locked_item)

                if job.state != 'tasked':
                    # This happens if a Job is cancelled while it's calling this
                    log.info("Job %s has state %s in complete_job" % (job.id, job.state))
                    return

                self._complete_job(job, errored, cancelled)

            with transaction.commit_on_success():
                self._drain_notification_buffer()
                self._run_next()

    @transaction.commit_on_success
    def create_host_ssh(self, address, root_pw=None, pkey=None, pkey_pw=None):
        """Agent boot strap the storage host at this address

        :param address the resolveable address of the host option user@ in front

        :param pw is either the root password, or the password that goes with
        the user if address is user@address, or, pw is it is the password of
        the private key if a pkey is specified.

        :param pkey is the private key that matches the public keys installed on the
        server at this address.
        """
        from chroma_core.services.job_scheduler.agent_rpc import AgentSsh

        # Commit token so that registration request handler will see it
        with transaction.commit_on_success():
            token = RegistrationToken.objects.create(credits = 1)

        agent_ssh = AgentSsh(address)
        auth_args = agent_ssh.construct_ssh_auth_args(root_pw, pkey, pkey_pw)

        args = {
            'url': settings.SERVER_HTTP_URL + "agent/",
            'address': address,
            'ca': open(Crypto().authority_cert).read().strip(),
            'secret': token.secret}
        result = agent_ssh.invoke('register_server', args, auth_args=auth_args)
        return result['host_id'], result['command_id']

    def test_host_contact(self, address, root_pw=None, pkey=None, pkey_pw=None):
        """Test that a host at this address can be created

        See create_host_ssh for explanation of parameters

        TODO: Break this method up, normalize the checks

        Use threaded timeouts on possible long running commands.  The idea is
        that if the command takes longer than the timeout, you might get a
        false negative - the command didn't fail, we just cut it short.
        Not sure this is an issue in practice, so going to stop here no ticket.
        """

        from chroma_core.services.job_scheduler.agent_rpc import AgentSsh

        agent_ssh = AgentSsh(address)
        user, hostname, port = agent_ssh.ssh_params()

        auth = False
        reverse_resolve = False
        reverse_ping = False

        auth_args = agent_ssh.construct_ssh_auth_args(root_pw, pkey, pkey_pw)

        try:
            resolved_address = socket.gethostbyname(hostname)
        except socket.gaierror:
            resolve = False
            ping = False
        else:
            resolve = True
            ping = (0 == subprocess.call(['ping', '-c 1', resolved_address]))

        if resolve:
            manager_hostname = urlparse.urlparse(settings.SERVER_HTTP_URL).hostname
            try:
                rc, out, err = agent_ssh.ssh(
                    "ping -c 1 %s" % manager_hostname,
                    auth_args=auth_args)
                auth = True
            except (AuthenticationException, SSHException):
                #  No auth methods available, or wrong creds
                auth = False
            except Exception, e:
                log.error("Error trying to invoke agent on '%s': %s" % (resolved_address, e))
                reverse_resolve = False
                reverse_ping = False
            else:
                if rc == 0:
                    reverse_resolve = True
                    reverse_ping = True
                elif rc == 1:
                    # Can resolve, cannot ping
                    reverse_resolve = True
                    reverse_ping = False
                else:
                    # Cannot resolve
                    reverse_resolve = False
                    reverse_ping = False
        else:
            auth = False
            reverse_resolve = False
            reverse_ping = False

        # Don't depend on ping to try invoking agent, could well have
        # SSH but no ping
        agent = False
        if resolve:
            try:
                agent_ssh.invoke('test', auth_args=auth_args)
                agent = True
                auth = True
            except (AuthenticationException, SSHException):
                #  No auth methods available, or wrong creds
                auth = False
            except Exception, e:
                log.error("Error trying to invoke agent on '%s': %s" % (resolved_address, e))
                agent = False

        return {
            'address': address,
            'resolve': resolve,
            'ping': ping,
            'auth': auth,
            'agent': agent,
            'reverse_resolve': reverse_resolve,
            'reverse_ping': reverse_ping
        }

    @classmethod
    def order_targets(cls, targets_data):
        "Return sorted sequence of target_data dicts, such that sequential OSTs will be distributed across hosts."
        volumes_ids = map(operator.itemgetter('volume_id'), targets_data)
        host_ids = dict(VolumeNode.objects.filter(volume_id__in=volumes_ids, primary=True).values_list('volume_id', 'host_id'))
        key = lambda td: host_ids[int(td['volume_id'])]
        for host_id, target_group in itertools.groupby(sorted(targets_data, key=key), key=key):
            for index, target_data in enumerate(target_group):
                target_data['index'] = index
        return sorted(targets_data, key=operator.itemgetter('index'))

    def create_filesystem(self, fs_data):
        # FIXME: HYD-970: check that the MGT or hosts aren't being removed while
        # creating the filesystem

        def _target_kwargs(attrs):
            result = {}
            for attr in ['inode_count', 'inode_size', 'bytes_per_inode']:
                try:
                    result[attr] = attrs[attr]
                except KeyError:
                    pass
            return result

        with self._lock:
            mounts = []
            mgt_data = fs_data['mgt']
            if 'volume_id' in mgt_data:
                mgt, mgt_mounts = ManagedMgs.create_for_volume(mgt_data['volume_id'], reformat=mgt_data.get('reformat', False), **_target_kwargs(mgt_data))
                mounts.extend(mgt_mounts)
                ObjectCache.add(ManagedTarget, mgt.managedtarget_ptr)
                mgt_id = mgt.pk
            else:
                mgt_id = mgt_data['id']

            from django.db import transaction
            with transaction.commit_on_success():
                mgs = ManagedMgs.objects.get(id = mgt_id)
                fs = ManagedFilesystem(mgs=mgs, name = fs_data['name'])
                fs.save()

                chroma_core.lib.conf_param.set_conf_params(fs, fs_data['conf_params'])

                mdt_data = fs_data['mdt']
                mdt, mdt_mounts = ManagedMdt.create_for_volume(mdt_data['volume_id'], reformat=mdt_data.get('reformat', False), filesystem = fs, **_target_kwargs(mdt_data))
                mounts.extend(mdt_mounts)
                chroma_core.lib.conf_param.set_conf_params(mdt, mdt_data['conf_params'])

                osts = []
                for ost_data in self.order_targets(fs_data['osts']):
                    ost, ost_mounts = ManagedOst.create_for_volume(ost_data['volume_id'],
                                                                   reformat=ost_data.get('reformat', False),
                                                                   filesystem=fs, **_target_kwargs(ost_data))
                    osts.append(ost)
                    mounts.extend(ost_mounts)
                    chroma_core.lib.conf_param.set_conf_params(ost, ost_data['conf_params'])

            # Now that the creation has committed, update ObjectCache
            ObjectCache.add(ManagedFilesystem, fs)
            for ost in osts:
                ObjectCache.add(ManagedTarget, ost.managedtarget_ptr)
            ObjectCache.add(ManagedTarget, mdt.managedtarget_ptr)
            for mount in mounts:
                ObjectCache.add(ManagedTargetMount, mount)

            with transaction.commit_on_success():
                command = CommandPlan(self._lock_cache, self._job_collection).command_set_state(
                    [(ContentType.objects.get_for_model(fs).natural_key(), fs.id, 'available')],
                    "Creating filesystem %s" % fs_data['name'])

        self.progress.advance()

        return fs.id, command.id

    def create_targets(self, targets_data):
        # FIXME: HYD-970: check that the filesystem or hosts aren't being removed while
        # creating the target

        targets = []
        with self._lock:
            for target_data in self.order_targets(targets_data):
                target_class = ContentType.objects.get_by_natural_key(*(target_data['content_type'])).model_class()
                if target_class == ManagedOst:
                    fs = ManagedFilesystem.objects.get(id=target_data['filesystem_id'])
                    create_kwargs = {'filesystem': fs}
                elif target_class == ManagedMgs:
                    create_kwargs = {}
                else:
                    raise NotImplementedError(target_class)

                with transaction.commit_on_success():
                    target, target_mounts = target_class.create_for_volume(
                        target_data['volume_id'], reformat=target_data.get('reformat', False), **create_kwargs)

                ObjectCache.add(ManagedTarget, target.managedtarget_ptr)
                for mount in target_mounts:
                    ObjectCache.add(ManagedTargetMount, mount)

                targets.append(target)

            if len(targets) == 1:
                command_description = "Creating %s" % targets[0]
            else:
                command_description = "Creating %s targets" % len(targets)

            with transaction.commit_on_success():
                command = CommandPlan(self._lock_cache, self._job_collection).command_set_state(
                    [(ContentType.objects.get_for_model(ManagedTarget).natural_key(), target.id, 'mounted') for target in targets],
                    command_description)

        self.progress.advance()

        return [target.id for target in targets], command.id

    def create_host(self, fqdn, nodename, capabilities, address):
        immutable_state = not any("manage_" in c for c in capabilities)

        with self._lock:
            with transaction.commit_on_success():
                host = ManagedHost.objects.create(
                    fqdn = fqdn,
                    nodename = nodename,
                    immutable_state = immutable_state,
                    address = address)
                lnet_configuration = LNetConfiguration.objects.create(host = host)

            ObjectCache.add(LNetConfiguration, lnet_configuration)
            ObjectCache.add(ManagedHost, host)

            with transaction.commit_on_success():
                command = CommandPlan(self._lock_cache, self._job_collection).command_set_state(
                    [(ContentType.objects.get_for_model(host).natural_key(), host.id, 'configured')],
                    "Setting up host %s" % host)

        self.progress.advance()

        return host.id, command.id
