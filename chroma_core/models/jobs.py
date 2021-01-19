# coding=utf-8
# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import uuid

from collections import defaultdict, namedtuple

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from polymorphic.models import DowncastMetaclass
from chroma_core.models.utils import DeletableDowncastableMetaclass

from chroma_core.lib.job import DependOn, DependAll, job_log
from chroma_core.lib.util import all_subclasses

MAX_STATE_STRING = 32


class SchedulingError(Exception):
    """An operation could not be fulfilled either because the transition
    change requested would leave the system in an invalid state, or because
    the transition has requirements which cannot be met"""

    pass


class StatefulObject(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True
        app_label = "chroma_core"

    state_modified_at = models.DateTimeField()
    state = models.CharField(max_length=MAX_STATE_STRING)
    immutable_state = models.BooleanField(default=False)
    states = None
    initial_state = None
    route_map = None
    transition_map = None
    job_class_map = None

    reverse_deps = {}

    def __init__(self, *args, **kwargs):
        super(StatefulObject, self).__init__(*args, **kwargs)

        if not self.state:
            self.state = self.initial_state

        if not self.state_modified_at:
            self.state_modified_at = now()

    def set_state(self, state, intentional=False):
        job_log.info(
            "StatefulObject.set_state %s %s->%s (intentional=%s) %s" % (self, self.state, state, intentional, id(self))
        )
        self.state = state
        self.state_modified_at = now()

    def not_state(self, state):
        return list(set(self.states) - set([state]))

    def not_states(self, states):
        return list(set(self.states) - set(states))

    def get_deps(self, state=None):
        """Return static dependencies, e.g. a targetmount in state
        mounted has a dependency on a host in state lnet_started but
        can get rid of it by moving to state unmounted"""
        return DependAll()

    @staticmethod
    def so_root(klass):
        """
        We looked for two things to find first class that contains its own route_map. This is basically the parent
        of the tree of objects. If we don't find that then we find the ancestor of klass which is a direct descendent
        of StatefulObject
        """

        # We do this because if I'm e.g. a ManagedMgs, I need to get my parent ManagedTarget
        # class in order to find out what jobs are applicable to me.
        # However if a child wants to actually have its own jobs it can do this by defining its own class method
        # route_map
        assert issubclass(klass, StatefulObject)

        if StatefulObject in klass.__bases__ or "route_map" in klass.__dict__:
            return klass
        else:
            for b in klass.__bases__:
                if hasattr(b, "_meta") and b._meta.abstract:
                    continue
                if issubclass(b, StatefulObject):
                    return StatefulObject.so_root(b)
            # Fallthrough: got as close as we're going
            return klass

    @classmethod
    def _build_maps(cls):
        """Populate route_map and transition_map attributes by introspection of
        this class and related StateChangeJob classes.  It is legal to call this
        twice or concurrently.
        """
        if cls.route_map is not None:
            return

        cls_ = StatefulObject.so_root(cls)

        transition_classes = [
            s
            for s in all_subclasses(StateChangeJob)
            if ((s.state_transition is not None) and (s.state_transition.class_ == cls_))
        ]
        transition_options = defaultdict(list)
        job_class_map = {}
        for c in transition_classes:
            to_state = c.state_transition.new_state
            if isinstance(c.state_transition.old_state, list):
                from_states = c.state_transition.old_state
            else:
                from_states = [c.state_transition.old_state]

            for from_state in from_states:
                transition_options[from_state].append(to_state)
                job_class_map[(from_state, to_state)] = c

        transition_map = defaultdict(list)
        route_map = {}
        for begin_state in cls_.states:
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

        cls_.route_map = route_map
        cls_.transition_map = transition_map

        cls_.job_class_map = job_class_map

    @classmethod
    def get_route(cls, begin_state, end_state):
        """Return an iterable of state strings, which is navigable using StateChangeJobs"""
        for s in begin_state, end_state:
            if not s in cls.states:
                raise SchedulingError("%s not legal state for %s, legal states are %s" % (s, cls, cls.states))

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
                raise SchedulingError(
                    "%s not legal state for %s, legal states are %s" % (begin_state, self.__class__, self.states)
                )

            if self.transition_map is None:
                self.__class__._build_maps()

            return list(set(self.transition_map[begin_state]))

    def get_verb(self, begin_state, end_state):
        """Return the GUI short (verb) and long description of the Job that is last in the route between the states

        begin_state need not be adjacent to the end_state, but but there must be a transitive route between them
        """

        job_cls = self.get_job_class(begin_state, end_state, last_job_in_route=True)
        return {"state_verb": job_cls.state_verb, "long_description": job_cls.get_long_description(self)}

    def get_job_class(self, begin_state, end_state, last_job_in_route=False):
        """Get the Job class that can be used to move any appropriate StatefulObject from begin_state to end_state

        By default, the begin_state and end_state must be adjacent
        (i.e. get from one to another with one StateChangeJob)

        if last_job_in_route is True, however, then the begin_state and end_state need not be adjacent
        (i.e. get from one to the other with more then one StateChangeJob).  In this case, the Job class returned
        is the last job in the list of jobs required.
        """

        self._build_maps()

        if last_job_in_route:
            route = self.route_map[(begin_state, end_state)]
            return self.job_class_map[(route[-2], route[-1])]
        else:
            return self.job_class_map[(begin_state, end_state)]

    def get_dependent_objects(self, inclusive=False):
        """Get all objects which MAY be depending on the state of this object"""

        # Cache mapping a class to a list of functions for getting
        # dependents of an instance of that class.
        if not hasattr(StatefulObject, "reverse_deps_map"):
            reverse_deps_map = defaultdict(list)
            for klass in all_subclasses(StatefulObject):
                for class_name, lookup_fn in klass.reverse_deps.items():
                    import chroma_core.models

                    # FIXME: looking up class this way eliminates our ability to move
                    # StatefulObject definitions out into other modules
                    so_class = getattr(chroma_core.models, class_name)
                    reverse_deps_map[so_class].append(lookup_fn)
            StatefulObject.reverse_deps_map = reverse_deps_map

        klass = StatefulObject.so_root(self.__class__)

        from itertools import chain

        lookup_fns = StatefulObject.reverse_deps_map[klass]
        querysets = set(chain(*[fn(self) for fn in lookup_fns]))

        if inclusive:
            querysets |= set(chain(*[x.get_dependent_objects() for x in querysets]))

        return querysets

    def cancel_current_operations(self):
        pass


class DeletableStatefulObject(StatefulObject):
    """Use this class to create your own downcastable classes if you need to override 'save', because
    using the metaclass directly will override your own save method"""

    __metaclass__ = DeletableDowncastableMetaclass

    class Meta:
        abstract = True
        app_label = "chroma_core"
        ordering = ["id"]


class StateLock(object):
    def __init__(self, job, locked_item, write, begin_state=None, end_state=None):
        self.uuid = str(uuid.uuid4())
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
        d = dict([(k, getattr(self, k)) for k in ["uuid", "write", "begin_state", "end_state"]])
        d["locked_item_id"] = self.locked_item.id
        d["locked_item_type_id"] = ContentType.objects.get_for_model(self.locked_item).id
        return d

    @classmethod
    def from_dict(cls, job, d):
        return StateLock(
            locked_item=ContentType.objects.get_for_id(d["locked_item_type_id"])
            .model_class()
            ._base_manager.get(pk=d["locked_item_id"]),
            job=job,
            write=d["write"],
            begin_state=d["begin_state"],
            end_state=d["end_state"],
        )


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

    states = ("pending", "tasked", "complete")
    state = models.CharField(max_length=16, default="pending", help_text="One of %s" % (states,))

    errored = models.BooleanField(
        default=False,
        help_text="True if the job has completed\
            with an error",
    )
    cancelled = models.BooleanField(
        default=False,
        help_text="True if the job has completed\
            as a result of a user cancelling it, or if it never started because of a failed\
            dependency",
    )

    modified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    wait_for_json = models.TextField()
    locks_json = models.TextField()

    @classmethod
    def long_description(cls, stateful_object):
        raise NotImplementedError("long_description needs to be implemented for each job.")

    # Job subclasses can provide one of these group values to assert the job group assignment
    JOB_GROUPS = namedtuple("GROUPS", "COMMON, INFREQUENT, RARE, EMERGENCY, LAST_RESORT, DEFAULT")(1, 2, 3, 4, 5, 1000)

    # The UX may display Jobs grouped.  Exactly how this happens is not defined in the backend.  But, you can control
    # the relative group of a job by specificing a 'group' attribute and assigning it to a choice from the GROUP
    # object above.  The default is to have the DEFAULT group.  This group will probably appear last.
    display_group = JOB_GROUPS.DEFAULT

    # display_order is a numeric index of the relative position of the job in a list.  Jobs are presented in different
    # contexts in the UI, typically defined by state and object type a job would act on.  This makes the order a bit
    # course grained, as this is the order to cover all cases.  Job subclasses provide display_order attrs.
    # appear at the top, and 2's after, an so on.  It is important for you to know roughly what jobs will appear
    # together at any presentation the application in in order to set this properly.  Look at the jobs you'd typically
    # see in a list, and look at their order attributes.  Trying to fit any new jobs in.  There can be gaps in the
    # sequence of numbers.  The intent is that the Job will be sorted numerically ascending.
    display_order = DEFAULT_ORDER = 1000

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
        app_label = "chroma_core"
        ordering = ["id"]

    def create_locks(self):
        return []

    @classmethod
    def can_run(cls, instance):
        """Return True if this Job can be run on the given instance"""
        return True

    def get_deps(self):
        return DependAll()

    def get_steps(self):
        return []

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
                    if (
                        dependent_dependency.stateful_object == stateful_object
                        and not new_state in dependent_dependency.acceptable_states
                    ):
                        dependent_deps.append(DependOn(dependent, dependent_dependency.fix_state))

            return DependAll(
                DependAll(dependent_deps),
                dep_cache.get(self),
                dep_cache.get(stateful_object, new_state),
                DependOn(stateful_object, self.old_state),
            )
        else:
            return dep_cache.get(self)

    def _deps_satisfied(self, dep_cache):
        from chroma_core.lib.job import job_log

        result = self.all_deps(dep_cache).satisfied()

        job_log.debug("Job %s: deps satisfied=%s" % (self.id, result))
        for d in self.all_deps(dep_cache).all():
            satisfied = d.satisfied()
            job_log.debug(
                "  %s %s (actual %s) %s" % (d.stateful_object, d.acceptable_states, d.stateful_object.state, satisfied)
            )
        return result

    def description(self):
        raise NotImplementedError

    def on_success(self):
        pass

    def on_error(self):
        """Method called by JobScheduler when a job is completed with job.errored=True

        This allows Job subclasses to do related processing at the time that the JobScheduler has determined the job
        failed.

        NB: The JobScheduler expects this to return nicely.  Do not raise exceptions or let known exceptions
        propagate from here.  If you do, that will be seen as a bug and probably crash the JobScheduler.  If you can
        control the raising of expections, please do.  This approach ensures that actual bugs are not masked."""
        pass

    def __str__(self):
        if self.id:
            id = self.id
        else:
            id = "unsaved"
        try:
            return "%s (Job %s)" % (self.description(), id)
        except NotImplementedError:
            return "<Job %s>" % id


class StateChangeJob(Job):
    """Subclasses must define a class attribute 'stateful_object'
    identifying another attribute which returns a StatefulObject"""

    old_state = models.CharField(max_length=MAX_STATE_STRING)

    StateTransition = namedtuple("StateTransition", ["class_", "old_state", "new_state"])
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
            raise RuntimeError("Using get_stateful_object outside of job_scheduler?")
        return self._so_cache

    def on_success(self):
        obj = self.get_stateful_object()
        new_state = self.state_transition.new_state
        obj.set_state(new_state, intentional=True)
        obj.save()
        job_log.info("Job %d: StateChangeJob complete, setting state %s on %s" % (self.pk, new_state, obj))
        if hasattr(obj, "not_deleted"):
            job_log.debug("Job %d: %s" % (self.id, id(obj)))
            job_log.info("Job %d: not_deleted=%s" % (self.id, obj.not_deleted))


class NullStateChangeJob(StateChangeJob):
    """
    A null state change job is one which the state changes but no actions take place.
    """

    state_transition = StateChangeJob.StateTransition(None, None, None)
    stateful_object = "target_object"
    _long_description = ""
    _description = ""

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 20

    class Meta:
        abstract = True

    @classmethod
    def long_description(cls, stateful_object):
        return cls._long_description


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
