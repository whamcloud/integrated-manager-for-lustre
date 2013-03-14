#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from picklefield.fields import PickledObjectField
from polymorphic.models import DowncastMetaclass

from chroma_core.lib.job import DependOn, DependAll, job_log
from chroma_core.lib.util import all_subclasses

MAX_STATE_STRING = 32


class SchedulingError(Exception):
    """An operation could not be fulfilled either because the transition
    change requested would leave the system in an invalid state, or because
    the transition has requirements which cannot be met"""
    pass


class Command(models.Model):
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
    created_at = models.DateTimeField(auto_now_add = True)

    dismissed = models.BooleanField(default=False,
                                    help_text = "``true``  denotes that the "
                                                "user has acknowledged this "
                                                "command's failure.")

    @classmethod
    def set_state(cls, objects, message = None, **kwargs):
        """The states argument must be a collection of 2-tuples
        of (<StatefulObject instance>, state)"""

        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

        dirty = False
        for object, state in objects:
            # Check if the state is modified
            if object.state != state:
                dirty = True
                break

            # Check if the new state is valid
            if state not in object.states:
                raise SchedulingError("'%s' is an invalid state for %s, valid states are %s" % (state, object, object.states))

        if not dirty:
            return None

        if not message:
            old_state = object.state
            new_state = state
            route = object.get_route(old_state, new_state)
            from chroma_core.services.job_scheduler.command_plan import Transition
            job = Transition(object, route[-2], route[-1]).to_job()
            message = job.description()

        object_ids = [(ContentType.objects.get_for_model(object).natural_key(), object.id, state) for object, state in objects]
        command_id = JobSchedulerClient.command_set_state(object_ids, message, **kwargs)

        return Command.objects.get(pk = command_id)

    def __repr__(self):
        return "<Command %s: '%s'>" % (self.id, self.message)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class StatefulObject(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True
        app_label = 'chroma_core'

    state_modified_at = models.DateTimeField()
    state = models.CharField(max_length = MAX_STATE_STRING)
    immutable_state = models.BooleanField(default=False)
    states = None
    initial_state = None

    reverse_deps = {}

    def __init__(self, *args, **kwargs):
        super(StatefulObject, self).__init__(*args, **kwargs)

        if not self.state:
            self.state = self.initial_state

        if not self.state_modified_at:
            self.state_modified_at = now()

    def set_state(self, state, intentional = False):
        job_log.info("StatefulObject.set_state %s %s->%s (intentional=%s)" % (self, self.state, state, intentional))
        self.state = state
        self.state_modified_at = now()
        self.__class__._base_manager.filter(pk = self.id).update(
            state = self.state,
            state_modified_at = self.state_modified_at)

    def not_state(self, state):
        return list(set(self.states) - set([state]))

    def not_states(self, states):
        return list(set(self.states) - set(states))

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
                raise SchedulingError("%s not legal state for %s, legal states are %s" % (s, cls, cls.states))

        if not hasattr(cls, 'route_map'):
            cls._build_maps()

        try:
            return cls.route_map[(begin_state, end_state)]
        except KeyError:
            raise SchedulingError("%s->%s not legal state transition for %s" % (begin_state, end_state, cls))

    def get_available_states(self, begin_state):
        """States which should be advertised externally (i.e. exclude states which
        are used internally but don't make sense when requested externally, for example
        the 'removed' state for an MDT (should only be reached by removing the owning filesystem)"""
        if self.immutable_state:
            return []
        else:
            if not begin_state in self.states:
                raise SchedulingError("%s not legal state for %s, legal states are %s" % (begin_state, self.__class__, self.states))

            if not hasattr(self, 'transition_map'):
                self.__class__._build_maps()

            return list(set(self.transition_map[begin_state]))

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


class StateLock(object):
    def __init__(self, job, locked_item, write, begin_state = None, end_state = None):
        self.job = job
        self.locked_item = locked_item
        self.write = write
        self.begin_state = begin_state
        self.end_state = end_state

    def __repr__(self):
        return "<%s>" % self.__str__()

    def __str__(self):
        if not self.write:
            return "Job %s readlock on %s" % (self.job.id, self.locked_item)
        else:
            return "Job %s writelock on %s %s->%s" % (self.job.id, self.locked_item, self.begin_state, self.end_state)

    def to_dict(self):
        d = dict([(k, getattr(self, k)) for k in ['write', 'begin_state', 'end_state']])
        d['locked_item_id'] = self.locked_item.id
        d['locked_item_type_id'] = ContentType.objects.get_for_model(self.locked_item).id
        return d

    @classmethod
    def from_dict(cls, job, d):
        return StateLock(
            locked_item = ContentType.objects.get_for_id(d['locked_item_type_id']).model_class()._base_manager.get(pk = d['locked_item_id']),
            job = job,
            write = d['write'],
            begin_state = d['begin_state'],
            end_state = d['end_state'])


class Job(models.Model):
    # Hashing functions are specialized to how jobs are used/indexed inside CommandPlan
    # - eq+hash operations are for operating on unsaved jobs
    # - which doesn't work properly by default (https://code.djangoproject.com/ticket/18250)
    # - and we also want the saved version of a job to compare equal to its unsaved version
    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return hash(id(self))

    __metaclass__ = DowncastMetaclass

    states = ('pending', 'tasked', 'complete')
    state = models.CharField(max_length = 16, default = 'pending',
                             help_text = "One of %s" % (states,))

    errored = models.BooleanField(default = False, help_text = "True if the job has completed\
            with an error")
    cancelled = models.BooleanField(default = False, help_text = "True if the job has completed\
            as a result of a user cancelling it, or if it never started because of a failed\
            dependency")

    modified_at = models.DateTimeField(auto_now = True)
    created_at = models.DateTimeField(auto_now_add = True)

    wait_for_json = models.TextField()
    locks_json = models.TextField()

    # Job classes declare whether presentation layer should
    # request user confirmation (e.g. removals, stops)
    def get_requires_confirmation(self):
        return False

    # If running this job has a string which should
    # be presented to the user for confirmations
    def get_confirmation_string(self):
        return None

    #: Whether the job can be safely cancelled
    cancellable = True

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def create_locks(self):
        return []

    def get_deps(self):
        return DependAll()

    def get_steps(self):
        raise NotImplementedError()

    def all_deps(self, dep_cache):
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
                for dependent_dependency in dep_cache.get(dependent).all():
                    if dependent_dependency.stateful_object == stateful_object \
                            and not new_state in dependent_dependency.acceptable_states:
                        dependent_deps.append(DependOn(dependent, dependent_dependency.fix_state))

            return DependAll(
                    DependAll(dependent_deps),
                    dep_cache.get(self),
                    dep_cache.get(stateful_object, new_state),
                    DependOn(stateful_object, self.old_state))
        else:
            return dep_cache.get(self)

    def _deps_satisfied(self, dep_cache):
        from chroma_core.lib.job import job_log

        result = self.all_deps(dep_cache).satisfied()

        job_log.debug("Job %s: deps satisfied=%s" % (self.id, result))
        for d in self.all_deps(dep_cache).all():
            satisfied = d.satisfied()
            job_log.debug("  %s %s (actual %s) %s" % (d.stateful_object, d.acceptable_states, d.stateful_object.state, satisfied))
        return result

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

    log = models.TextField(help_text = "Human readable summary of progress during execution.")

    console = models.TextField(help_text = "Combined standard out and standard error from all\
            subprocesses run while completing this step.  This includes output from successful\
            as well as unsuccessful commands, and may be very verbose.")
    backtrace = models.TextField(help_text = "Backtrace of an exception, if one occurred")

    # FIXME: we should have a 'cancelled' state for when a step is running while its job is cancelled
    state = models.CharField(max_length = 32, default='incomplete', help_text = 'One of incomplete, failed, success')

    modified_at = models.DateTimeField(auto_now = True)
    created_at = models.DateTimeField(auto_now_add = True)

    def step_klass_name(self):
        """Template helper"""
        return self.step_klass.__name__

    def describe(self):
        return self.step_klass.describe(self.args)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


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

    def __init__(self, *args, **kwargs):
        super(StateChangeJob, self).__init__(*args, **kwargs)
        if self.stateful_object in kwargs:
            self._so_cache = kwargs[self.stateful_object]
        else:
            self._so_cache = None

    class Meta:
        abstract = True

    def get_stateful_object(self):
        if not self._so_cache:
            stateful_object = getattr(self, self.stateful_object)
            # Get a fresh instance every time, we don't want one hanging around in the job
            # run procedure because steps might be modifying it
            stateful_object = stateful_object.__class__._base_manager.get(pk = stateful_object.pk)
            if hasattr(stateful_object, 'content_type'):
                stateful_object = stateful_object.downcast()
            self._so_cache = stateful_object
        return self._so_cache


class AdvertisedJob(Job):
    """A job which is offered for execution in relation to particular objects"""
    class Meta:
        abstract = True

    # list of classes e.g. ['ManagedHost'] of the class
    # on which this can be run
    classes = None

    # Terse human readable verb, e.g. "Launch Torpedos"
    verb = None

    # If False, running this job on N objects is N jobs, if True then running
    # this job on N objects is one job.
    plural = False

    @classmethod
    def can_run(cls, instance):
        """Return True if this Job can be run on the given instance"""
        return True

    @classmethod
    def get_args(cls, objects):
        """
        :param objects: For if cls.plural then an iterable of objects, else a single object

        Return a dict of args suitable for constructing an instance of this class operating
        on a particular object instance"""
        raise NotImplementedError()

    @classmethod
    def get_confirmation(cls, instance):
        """Return a string for the confirmation prompt, or None if no confirmation is needed"""
        return None
