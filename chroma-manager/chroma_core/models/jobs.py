#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime

from django.db import models
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from picklefield.fields import PickledObjectField

from chroma_core.models.utils import WorkaroundGenericForeignKey, WorkaroundDateTimeField, await_async_result

from django.db.models import Q
from collections import defaultdict
from polymorphic.models import DowncastMetaclass
from chroma_core.lib.job import DependOn, DependAll
from chroma_core.lib.util import all_subclasses

MAX_STATE_STRING = 32


class Command(models.Model):
    jobs_created = models.BooleanField(default = False,
        help_text = "True if the jobs for this command have been scheduled.\
                Commands start with this False, as scheduling the jobs for a\
                command is an asynchronous process.")
    jobs = models.ManyToManyField('Job')

    complete = models.BooleanField(default = False,
        help_text = "True if all jobs have completed, or no jobs were needed to \
                     satisfy the command")
    errored = models.BooleanField(default = False,
        help_text = "True if one or more of the command's jobs failed, or if \
        there was an error scheduling jobs for this command")
    cancelled = models.BooleanField(default = False,
            help_text = "True if one or more of the command's jobs completed\
            with its cancelled attribute set to True, or if this command\
            was cancelled by the user")
    message = models.CharField(max_length = 512,
            help_text = "Human readable string about one sentence long describing\
            the action being done by the command")
    created_at = WorkaroundDateTimeField(auto_now_add = True)

    @classmethod
    def set_state(cls, objects, message = None):
        """The states argument must be a collection of 2-tuples
        of (<StatefulObject instance>, state)"""
        dirty = False
        for object, state in objects:
            # Check if the state is modified
            if object.state != state:
                dirty = True
                break

            # Check if the new state is valid
            if state not in object.states:
                raise RuntimeError("'%s' is an invalid state for %s, valid states are %s" % (state, object, object.states))

        if not dirty:
            return None

        if not message:
            old_state = object.state
            new_state = state
            route = object.get_route(old_state, new_state)
            from chroma_core.lib.state_manager import Transition
            job = Transition(object, route[-2], route[-1]).to_job()
            message = job.description()

        object_ids = [(ContentType.objects.get_for_model(object).natural_key(), object.id, state) for object, state in objects]

        from chroma_core.tasks import command_set_state
        async_result = command_set_state.delay(
                object_ids,
                message)

        command_id = await_async_result(async_result)

        return Command.objects.get(pk = command_id)

    class Meta:
        app_label = 'chroma_core'


class OpportunisticJob(models.Model):
    job = PickledObjectField()
    run = models.BooleanField(default = False)
    run_at = WorkaroundDateTimeField(null = True, blank = True)

    class Meta:
        app_label = 'chroma_core'

    def get_job(self):
        job = self.job
        # Jobs here are meant to be unsaved instances
        assert not job.pk

        return job


class StatefulObject(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True
        app_label = 'chroma_core'

    state_modified_at = WorkaroundDateTimeField()
    state = models.CharField(max_length = MAX_STATE_STRING)
    immutable_state = models.BooleanField(default=False)
    states = None
    initial_state = None

    reverse_deps = {}

    def __init__(self, *args, **kwargs):
        super(StatefulObject, self).__init__(*args, **kwargs)

        if not self.state:
            self.state = self.initial_state
            self.state_modified_at = datetime.datetime.utcnow()

    def set_state(self, state):
        self.state = state
        self.state_modified_at = datetime.datetime.utcnow()
        self.save()

    def not_state(self, state):
        return list(set(self.states) - set([state]))

    def get_deps(self, state = None):
        """Return static dependencies, e.g. a targetmount in state
           mounted has a dependency on a host in state lnet_started but
           can get rid of it by moving to state unmounted"""
        return DependAll()

    @staticmethod
    def so_child(klass):
        """Find the ancestor of klass which is a direct descendent of StatefulObject"""
        # We do this because if I'm e.g. a ManagedMgs, I need to get my parent ManagedTarget
        # class in order to find out what jobs are applicable to me.
        assert(issubclass(klass, StatefulObject))

        if StatefulObject in klass.__bases__:
            return klass
        else:
            for b in klass.__bases__:
                if hasattr(b, '_meta') and b._meta.abstract:
                    continue
                if issubclass(b, StatefulObject):
                    return StatefulObject.so_child(b)
            # Fallthrough: got as close as we're going
            return klass

    @classmethod
    def _build_maps(cls):
        """Populate route_map and transition_map attributes by introspection of
           this class and related StateChangeJob classes.  It is legal to call this
           twice or concurrently."""
        cls = StatefulObject.so_child(cls)

        transition_classes = [s for s in all_subclasses(StateChangeJob) if s.state_transition[0] == cls]
        transition_options = defaultdict(list)
        job_class_map = {}
        for c in transition_classes:
            to_state = c.state_transition[2]
            if isinstance(c.state_transition[1], list):
                from_states = c.state_transition[1]
            else:
                from_states = [c.state_transition[1]]

            for from_state in from_states:
                transition_options[from_state].append(to_state)
                job_class_map[(from_state, to_state)] = c

        transition_map = defaultdict(list)
        route_map = {}
        for begin_state in cls.states:
            all_routes = set()

            # Enumerate all possible routes from this state
            def get_routes(stack, explore_state):
                if explore_state in stack:
                    all_routes.add(tuple(stack))
                    return

                stack = stack + [explore_state]

                if len(transition_options[explore_state]) == 0:
                    if len(stack) > 1:
                        all_routes.add(tuple(stack))
                    return

                for next_state in transition_options[explore_state]:
                    get_routes(stack, next_state)

            get_routes([], begin_state)

            # For all valid routes with more than 2 states,
            # all truncations of 2 or more states are also valid routes.
            truncations = set()
            for r in all_routes:
                for i in range(2, len(r)):
                    truncations.add(tuple(r[0:i]))
            all_routes = all_routes | truncations

            routes = defaultdict(list)
            # Build a map of end state to list of ways of getting there
            for route in all_routes:
                routes[route[-1]].append(route)

            # Pick the shortest route to each end state
            for (end_state, possible_routes) in routes.items():
                possible_routes.sort(lambda a, b: cmp(len(a), len(b)))
                shortest_route = possible_routes[0]

                transition_map[begin_state].append(end_state)
                route_map[(begin_state, end_state)] = shortest_route

        cls.route_map = route_map
        cls.transition_map = transition_map

        cls.job_class_map = job_class_map

    @classmethod
    def get_route(cls, begin_state, end_state):
        """Return an iterable of state strings, which is navigable using StateChangeJobs"""
        for s in begin_state, end_state:
            if not s in cls.states:
                raise RuntimeError("%s not legal state for %s, legal states are %s" % (s, cls, cls.states))

        if not hasattr(cls, 'route_map'):
            cls._build_maps()

        try:
            return cls.route_map[(begin_state, end_state)]
        except KeyError:
            raise RuntimeError("%s->%s not legal state transition for %s" % (begin_state, end_state, cls))

    def get_available_states(self, begin_state):
        """States which should be advertised externally (i.e. exclude states which
        are used internally but don't make sense when requested externally, for example
        the 'removed' state for an MDT (should only be reached by removing the owning filesystem)"""
        if self.immutable_state:
            # The only available state transition for immutable objects is
            # to a special "forgotten" state, which is a shortcut state
            # to allow us to get to what is effectively 'removed' without
            # passing through all the normal states (which would fail).
            return ['forgotten']

        if not begin_state in self.states:
            raise RuntimeError("%s not legal state for %s, legal states are %s" % (begin_state, self.__class__, self.states))

        if not hasattr(self, 'transition_map'):
            self.__class__._build_maps()

        # Conversely, 'forgotten' is never an available destination state
        # for manageable objects.  They can be removed, but not forgotten.
        return list(set(self.transition_map[begin_state]) - set(['forgotten']))

    @classmethod
    def get_verb(cls, begin_state, end_state):
        """begin_state need not be adjacent but there must be a route between them"""
        if not hasattr(cls, 'route_map') or not hasattr(cls, 'job_class_map'):
            cls._build_maps()

        route = cls.route_map[(begin_state, end_state)]
        job_cls = cls.job_class_map[(route[-2], route[-1])]
        return job_cls.state_verb

    @classmethod
    def get_job_class(cls, begin_state, end_state):
        """begin_state and end_state must be adjacent (i.e. get from one to another
           with one StateChangeJob)"""
        if not hasattr(cls, 'route_map') or not hasattr(cls, 'job_class_map'):
            cls._build_maps()

        return cls.job_class_map[(begin_state, end_state)]

    def get_dependent_objects(self):
        """Get all objects which MAY be depending on the state of this object"""

        # Cache mapping a class to a list of functions for getting
        # dependents of an instance of that class.
        if not hasattr(StatefulObject, 'reverse_deps_map'):
            reverse_deps_map = defaultdict(list)
            for klass in all_subclasses(StatefulObject):
                for class_name, lookup_fn in klass.reverse_deps.items():
                    import chroma_core.models
                    #FIXME: looking up class this way eliminates our ability to move
                    # StatefulObject definitions out into other modules
                    so_class = getattr(chroma_core.models, class_name)
                    reverse_deps_map[so_class].append(lookup_fn)
            StatefulObject.reverse_deps_map = reverse_deps_map

        klass = StatefulObject.so_child(self.__class__)

        from itertools import chain
        lookup_fns = StatefulObject.reverse_deps_map[klass]
        querysets = [fn(self) for fn in lookup_fns]
        return chain(*querysets)


class StateLock(models.Model):
    """Lock is the wrong word really, these objects exist for the lifetime of the Job.
    All locks depend on the last pending job to write to a stateful object on which
    they hold claim read or write lock.
    """

    __metaclass__ = DowncastMetaclass
    job = models.ForeignKey('Job')

    locked_item_type = models.ForeignKey(ContentType, related_name = 'locked_item')
    locked_item_id = models.PositiveIntegerField()
    locked_item = WorkaroundGenericForeignKey('locked_item_type', 'locked_item_id')

    class Meta:
        app_label = 'chroma_core'

    @classmethod
    def filter_by_locked_item(cls, stateful_object):
        ctype = ContentType.objects.get_for_model(stateful_object)
        return cls.objects.filter(locked_item_type = ctype, locked_item_id = stateful_object.id)


class StateReadLock(StateLock):
    #locked_state = models.CharField(max_length = MAX_STATE_STRING)
    # NB we don't actually need to know the readlock state, although
    # it would be useful to store the acceptable_states of the DependOn
    # to validate that write locks left it in the right state.

    class Meta:
        app_label = 'chroma_core'

    def __str__(self):
        return "Job %d readlock on %s" % (self.job.id, self.locked_item)


class StateWriteLock(StateLock):
    begin_state = models.CharField(max_length = MAX_STATE_STRING)
    end_state = models.CharField(max_length = MAX_STATE_STRING)

    class Meta:
        app_label = 'chroma_core'

    def __str__(self):
        return "Job %d writelock on %s %s->%s" % (self.job.id, self.locked_item, self.begin_state, self.end_state)


class Job(models.Model):
    __metaclass__ = DowncastMetaclass

    states = ('pending', 'tasked', 'complete', 'completing', 'cancelling', 'paused')
    state = models.CharField(max_length = 16, default = 'pending',
                             help_text = "One of %s" % (states,))

    errored = models.BooleanField(default = False, help_text = "True if the job has completed\
            with an error")
    paused = models.BooleanField(default = False, help_text = "True if the job is currently\
            in a paused state")
    cancelled = models.BooleanField(default = False, help_text = "True if the job has completed\
            by a user cancelling it, or if it never started because of a failed\
            dependency")

    modified_at = WorkaroundDateTimeField(auto_now = True)
    created_at = WorkaroundDateTimeField(auto_now_add = True)

    wait_for_count = models.PositiveIntegerField(default = 0)
    wait_for_completions = models.PositiveIntegerField(default = 0)
    wait_for = models.ManyToManyField('Job', symmetrical = False, related_name = 'wait_for_job')

    task_id = models.CharField(max_length=36, blank = True, null = True)

    # Set to a step index before that step starts running
    started_step = models.PositiveIntegerField(default = None, blank = True, null = True,
            help_text = "Step which has been started within the Job")
    # Set to a step index when that step has finished and its result is committed
    finished_step = models.PositiveIntegerField(default = None, blank = True, null = True,
            help_text = "Step which has been finished within the job, if not equal\
                    to started_step then a step is in progress.")

    # Job classes declare whether presentation layer should
    # request user confirmation (e.g. removals, stops)
    def get_requires_confirmation(self):
        return False

    # If running this job has a string which should
    # be presented to the user for confirmations
    def get_confirmation_string(self):
        return None

    #: Whether the job should be added to opportunistic Job queue if it doesn't run
    #  successfully.
    opportunistic_retry = False

    class Meta:
        app_label = 'chroma_core'

    def task_state(self):
        from celery.result import AsyncResult
        return AsyncResult(self.task_id).state

    def notify_wait_for_complete(self):
        """Called by a wait_for job to notify that it is complete"""
        from django.db.models import F
        Job.objects.get_or_create(pk = self.id)
        Job.objects.filter(pk = self.id).update(wait_for_completions = F('wait_for_completions') + 1)

    def create_dependencies(self):
        """Examine overlaps between self's statelocks and those of
           earlier jobs which are still pending, and generate wait_for
           dependencies when we have a write lock and they have a read lock
           or generate depend_on dependencies when we have a read or write lock and
           they have a write lock"""
        wait_fors = set()
        for lock in self.statelock_set.all():
            if isinstance(lock, StateWriteLock):
                wl = lock
                # Depend on the most recent pending write to this stateful object,
                # trust that it will have depended on any before that.
                try:
                    prior_write_lock = StateWriteLock.filter_by_locked_item(wl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).latest('id')
                    assert (wl.begin_state == prior_write_lock.end_state), ("%s locks %s in state %s but previous %s leaves it in state %s" % (self, wl.locked_item, wl.begin_state, prior_write_lock.job, prior_write_lock.end_state))
                    wait_fors.add(prior_write_lock.job)
                    # We will only wait_for read locks after this write lock, as it
                    # will have wait_for'd any before it.
                    read_barrier_id = prior_write_lock.job.id
                except StateWriteLock.DoesNotExist:
                    read_barrier_id = 0
                    pass

                # Wait for any reads of the stateful object between the last write and
                # our position.
                prior_read_locks = StateReadLock.filter_by_locked_item(wl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).filter(job__id__gte = read_barrier_id)
                for i in prior_read_locks:
                    wait_fors.add(i.job)
            elif isinstance(lock, StateReadLock):
                rl = lock
                try:
                    prior_write_lock = StateWriteLock.filter_by_locked_item(rl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).latest('id')
                    # See comment by locked_state in StateReadLock
                    #assert(prior_write_lock.end_state == rl.locked_state)
                    wait_fors.add(prior_write_lock.job)
                except StateWriteLock.DoesNotExist:
                    pass

        for j in wait_fors:
            self.wait_for.add(j)
        self.wait_for_count = self.wait_for.count()
        self.save()

    def create_locks(self):
        # Take read lock on everything from self.get_deps
        for dependency in self.get_deps().all():
            StateReadLock.objects.create(job = self, locked_item = dependency.stateful_object)

        if isinstance(self, StateChangeJob):
            stateful_object = self.get_stateful_object()
            target_klass, origins, new_state = self.state_transition

            # Take read lock on everything from get_stateful_object's get_deps if
            # this is a StateChangeJob.  We do things depended on by both the old
            # and the new state: e.g. if we are taking a mount from unmounted->mounted
            # then we need to lock the new state's requirement of lnet_up, whereas
            # if we're going from mounted->unmounted we need to lock the old state's
            # requirement of lnet_up (to prevent someone stopping lnet while
            # we're still running)
            from itertools import chain
            for d in chain(stateful_object.get_deps(self.old_state).all(), stateful_object.get_deps(new_state).all()):
                StateReadLock.objects.create(job = self,
                        locked_item = d.stateful_object)

            # Take a write lock on get_stateful_object if this is a StateChangeJob
            StateWriteLock.objects.create(
                    job = self,
                    locked_item = stateful_object,
                    begin_state = self.old_state,
                    end_state = new_state)

    @classmethod
    def run_next(cls):
        from chroma_core.lib.job import job_log
        from django.db.models import F
        runnable_jobs = Job.objects \
            .filter(wait_for_completions = F('wait_for_count')) \
            .filter(state = 'pending')

        job_log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (
            runnable_jobs.count(),
            Job.objects.filter(state = 'pending').count(),
            Job.objects.filter(state = 'tasked').count()))
        for job in runnable_jobs:
            job.downcast().run()

    def get_deps(self):
        return DependAll()

    def get_steps(self):
        raise NotImplementedError()

    def cancel(self):
        from chroma_core.lib.job import job_log
        job_log.debug("Job %d: Job.cancel" % self.id)

        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.
        with transaction.commit_on_success():
            updated = Job.objects.filter(~Q(state = 'complete'), pk = self.id).update(state = 'cancelling')
        if updated == 0:
            # Someone else already started this job, bug out
            job_log.debug("job %d already completed, not cancelling" % self.id)
            return

        if self.task_id:
            job_log.debug("job %d: revoking task %s" % (self.id, self.task_id))
            from celery.task.control import revoke
            revoke(self.task_id, terminate = True)
            self.task_id = None

        self.complete(cancelled = True)

    def pause(self):
        from chroma_core.lib.job import job_log
        job_log.debug("Job %d: Job.pause" % self.id)

        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.
        @transaction.commit_on_success()
        def mark_paused():
            return Job.objects.filter(state = 'pending', pk = self.id).update(state = 'paused')

        updated = mark_paused()
        if updated != 1:
            job_log.warning("Job %d: failed to pause, it had already left state 'pending'")

    def unpause(self):
        from chroma_core.lib.job import job_log
        job_log.debug("Job %d: Job.unpause" % self.id)

        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.
        @transaction.commit_on_success()
        def mark_unpaused():
            return Job.objects.filter(state = 'paused', pk = self.id).update(state = 'pending')

        updated = mark_unpaused()
        if updated != 1:
            job_log.warning("Job %d: failed to pause, it had already left state 'pending'" % self.id)
        else:
            job_log.warning("Job %d: unpaused, running any available jobs" % self.id)
            Job.run_next()

    def all_deps(self):
        # This is not necessarily 100% consistent with the dependencies used by StateManager
        # when the job was submitted (e.g. other models which get_deps queries may have
        # changed), but that is a *good thing* -- this is a last check before running
        # which will safely cancel the job if something has changed that breaks our deps.
        if isinstance(self, StateChangeJob):
            stateful_object = self.get_stateful_object()
            target_klass, origins, new_state = self.state_transition

            # Generate dependencies (which will fail) for any dependents
            # which depend on our old state (bit of a roundabout way of doing it)
            dependent_deps = []
            dependents = stateful_object.get_dependent_objects()
            for dependent in dependents:
                for dependent_dependency in dependent.get_deps().all():
                    if dependent_dependency.stateful_object == stateful_object \
                            and not new_state in dependent_dependency.acceptable_states:
                        dependent_deps.append(DependOn(dependent, dependent_dependency.fix_state))

            return DependAll(
                    DependAll(dependent_deps),
                    self.get_deps(),
                    stateful_object.get_deps(new_state),
                    DependOn(stateful_object, self.old_state))
        else:
            return self.get_deps()

    def _deps_satisfied(self):
        from chroma_core.lib.job import job_log

        try:
            result = self.all_deps().satisfied()
        except Exception, e:
            # Catchall exception handler to ensure progression even if Job
            # subclasses have bugs in their get_deps etc.
            job_log.error("Job %s: internal error %s" % (self.id, e))
            result = False

        job_log.debug("Job %s: deps satisfied=%s" % (self.id, result))
        for d in self.all_deps().all():
            satisfied = d.satisfied()
            job_log.debug("  %s %s (actual %s) %s" % (d.stateful_object, d.acceptable_states, d.stateful_object.state, satisfied))
        return result

    def run(self):
        from chroma_core.lib.job import job_log
        job_log.info("Job %d: Job.run %s" % (self.id, self.description()))
        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.

        # All the complexity of StateManager's dependency calculation doesn't
        # matter here: we've reached our point in the queue, all I need to check now
        # is - are this Job's immediate dependencies satisfied?  And are any deps
        # for a statefulobject's new state satisfied?  If so, continue.  If not, cancel.

        deps_satisfied = self._deps_satisfied()

        if not deps_satisfied:
            job_log.warning("Job %d: cancelling because of failed dependency" % (self.id))
            self.complete(cancelled = True)
            # TODO: tell someone WHICH dependency
            return

        # Set state to 'tasked'
        # =====================
        with transaction.commit_on_success():
            updated = Job.objects.filter(pk = self.id, state = 'pending').update(state = 'tasking')

        if updated == 0:
            # Someone else already started this job, bug out
            job_log.debug("Job %d already started running, backing off" % self.id)
            return
        else:
            assert(updated == 1)
            job_log.debug("Job %d pending->tasking" % self.id)
            self.state = 'tasking'

        # Generate a celery task
        # ======================
        from chroma_core.tasks import run_job
        celery_job = run_job.delay(self.id)

        # Save the celery task ID
        # =======================
        from celery.result import EagerResult
        if isinstance(celery_job, EagerResult):
            # Eager execution happens when under test
            job_log.debug("Job %d ran eagerly" % (self.id))
        else:
            self.task_id = celery_job.task_id
            self.state = 'tasked'
            self.save()
            job_log.debug("Job %d tasking->tasked (%s)" % (self.id, self.task_id))

    @classmethod
    def cancel_job(cls, job_id):
        job = Job.objects.get(pk = job_id)
        if job.state != 'tasked':
            return None

    def complete(self, errored = False, cancelled = False):
        from chroma_core.lib.job import job_log
        success = not (errored or cancelled)
        if success and isinstance(self, StateChangeJob):
            new_state = self.state_transition[2]
            with transaction.commit_on_success():
                obj = self.get_stateful_object()
                obj.set_state(new_state)
                job_log.info("Job %d: StateChangeJob complete, setting state %s on %s" % (self.pk, new_state, obj))

        job_log.info("Job %d completing (errored=%s, cancelled=%s)" %
                (self.id, errored, cancelled))
        with transaction.commit_on_success():
            self.state = 'completing'
            self.errored = errored
            self.cancelled = cancelled
            self.save()

        from chroma_core.lib.state_manager import StateManager
        StateManager.complete_job(self.pk)

    def description(self):
        raise NotImplementedError

    def __str__(self):
        if self.id:
            id = self.id
        else:
            id = 'unsaved'
        try:
            return "%s (Job %s)" % (self.description(), id)
        except NotImplementedError:
            return "<Job %s>" % id


class StepResult(models.Model):
    job = models.ForeignKey(Job)
    step_klass = PickledObjectField()
    args = PickledObjectField(help_text = 'Dictionary of arguments to this step')

    step_index = models.IntegerField(help_text = "Zero-based index of this step within the steps of\
            a job.  If a step is retried, then two steps can have the same index for the same job.")
    step_count = models.IntegerField(help_text = "Number of steps in this job")

    console = models.TextField(help_text = "For debugging: combined standard out and standard error from all\
            subprocesses run while completing this step.  This includes output from successful\
            as well as unsuccessful commands, and may be very verbose.")
    exception = PickledObjectField(blank = True, null = True, default = None)
    backtrace = models.TextField(help_text = "Backtrace of an exception, if the exception occurred\
            locally on the server.  Exceptions which occur remotely include the backtrace in the\
            ``exception`` field")

    # FIXME: we should have a 'cancelled' state for when a step
    # is running while its job is cancelled
    state = models.CharField(max_length = 32, default='incomplete', help_text = 'One of incomplete, failed, success')

    modified_at = WorkaroundDateTimeField(auto_now = True)
    created_at = WorkaroundDateTimeField(auto_now_add = True)

    def step_number(self):
        """Template helper"""
        return self.step_index + 1

    def step_klass_name(self):
        """Template helper"""
        return self.step_klass.__name__

    def describe(self):
        return self.step_klass.describe(self.args)

    class Meta:
        app_label = 'chroma_core'


class StateChangeJob(Job):
    """Subclasses must define a class attribute 'stateful_object'
       identifying another attribute which returns a StatefulObject"""

    old_state = models.CharField(max_length = MAX_STATE_STRING)

    # Tuple of (StatefulObjectSubclass, old_state, new_state)
    state_transition = None
    # Name of an attribute which is a ForeignKey to a StatefulObject
    stateful_object = None
    # Terse human readable verb, e.g. "Change this" (for buttons)
    state_verb = None

    class Meta:
        abstract = True

    def get_stateful_object_id(self):
        stateful_object = getattr(self, self.stateful_object)
        return stateful_object.pk

    def get_stateful_object(self):
        stateful_object = getattr(self, self.stateful_object)
        # Get a fresh instance every time, we don't want one hanging around in the job
        # run procedure because steps might be modifying it
        stateful_object = stateful_object.__class__._base_manager.get(pk = stateful_object.pk)
        return stateful_object
