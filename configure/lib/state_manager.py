#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from collections import defaultdict
from django.db import transaction
from configure.lib.job import job_log


class Transition(object):
    def __init__(self, stateful_object, old_state, new_state):
        self.stateful_object = stateful_object
        self.old_state = old_state
        self.new_state = new_state

    def __str__(self):
        return "%s %s->%s" % (self.stateful_object, self.old_state, self.new_state)

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return ("%s %s %s %s" % (self.stateful_object.__class__, self.stateful_object.id, self.old_state, self.new_state)).__hash__()

    def to_job(self):
        job_klass = self.stateful_object.get_job_class(self.old_state, self.new_state)
        stateful_object_attr = job_klass.stateful_object
        kwargs = {stateful_object_attr: self.stateful_object}
        return job_klass(**kwargs)


class StateManager(object):
    @classmethod
    def available_transitions(cls, stateful_object):
        """Return a list states to which the object can be set from
           its current state, or None if the object is currently
           locked by a Job"""
        # If the object is subject to an incomplete StateChangeJob
        # then don't offer any other transitions.
        from configure.models import StateLock
        from django.db.models import Q

        # We don't advertise transitions for anything which is currently
        # locked by an incomplete job.  We could alternatively advertise
        # which jobs would actually be legal to add by skipping this check and
        # using get_expected_state in place of .state below.
        active_locks = StateLock.filter_by_locked_item(stateful_object).filter(~Q(job__state = 'complete')).count()
        if active_locks > 0:
            return []

        # XXX: could alternatively use expected_state here if you want to advertise
        # what jobs can really be added (i.e. advertise transitions which will
        # be available when current jobs are complete)
        #from_state = self.get_expected_state(stateful_object)
        from_state = stateful_object.state
        available_states = stateful_object.get_available_states(from_state)
        return [
                {"state": to_state,
                "verb": stateful_object.get_verb(from_state, to_state)} for to_state in available_states]

    def get_expected_state(self, stateful_object_instance):
        try:
            return self.expected_states[stateful_object_instance]
        except KeyError:
            return stateful_object_instance.state

    @classmethod
    def notify_state(cls, instance, new_state, from_states):
        """from_states: list of states it's valid to transition from.  This lets
           the audit code safely update the state of e.g. a mount it doesn't find
           to 'unmounted' without risking incorrectly transitioning from 'unconfigured'"""
        if instance.state in from_states and instance.state != new_state:
            from configure.tasks import notify_state
            notify_state.delay(
                instance.content_type.natural_key(),
                instance.id,
                new_state,
                from_states)

    @classmethod
    def add_job(cls, job):
        from configure.tasks import add_job
        celery_task = add_job.delay(job)
        job_log.debug("add_job: celery task %s" % celery_task.task_id)

    def _add_job(self, job):
        """Add a job, and any others which are required in order to reach its prerequisite state"""
        for dependency in job.get_deps().all():
            if not dependency.stateful_object.state in dependency.acceptable_states:
                self._set_state(dependency.stateful_object, dependency.preferred_state)

        # Important: the Job must not be committed until all
        # its dependencies and locks are in.
        @transaction.commit_on_success
        def instantiate_job():
            job.save()
            job.create_locks()
            job.create_dependencies()
        instantiate_job()

        transaction.commit()
        from configure.models import Job
        Job.run_next()

    @classmethod
    def set_state(cls, instance, new_state):
        """Add a 0 or more Jobs to have 'instance' reach 'new_state'"""
        import configure.tasks
        from django.contrib.contenttypes.models import ContentType
        if not new_state in instance.states:
            raise RuntimeError("State '%s' is invalid for %s, must be one of %s" % (new_state, instance.__class__, instance.states))
        return configure.tasks.set_state.delay(
                ContentType.objects.get_for_model(instance).natural_key(),
                instance.id,
                new_state)

    def get_transition_consequences(self, instance, new_state):
        """For use in the UI, for warning the user when an
           action is going to have some consequences which
           affect an object other than the one they are operating
           on directly.  Because this is UI rather than business
           logic, we take some shortcuts here:
            * Don't calculate expected_states, i.e. ignore running
              jobs and generate output based on the actual committed
              states of objects
            * Don't bother sorting for execution order - output an
              unordered list.
        """
        from configure.models import StatefulObject
        assert(isinstance(instance, StatefulObject))

        self.expected_states = {}
        self.deps = set()
        self.edges = set()
        self.emit_transition_deps(Transition(
            instance,
            self.get_expected_state(instance),
            new_state))

        job_log.debug("Transition %s %s->%s:" % (instance, self.get_expected_state(instance), new_state))
        for d in self.deps:
            job_log.debug("  dep %s" % (d,))
        for e in self.edges:
            job_log.debug("  edge [%s]->[%s]" % (e))

        depended_jobs = []
        for d in self.deps:
            job = d.to_job()
            from configure.lib.job import StateChangeJob
            if isinstance(job, StateChangeJob):
                from django.contrib.contenttypes.models import ContentType
                so = getattr(job, job.stateful_object)
                stateful_object_id = so.pk
                stateful_object_content_type_id = ContentType.objects.get_for_model(so).pk
            else:
                stateful_object_id = None
                stateful_object_content_type_id = None
            depended_jobs.append({
                'class': job.__class__.__name__,
                'requires_confirmation': job.requires_confirmation,
                'description': job.description(),
                'stateful_object_id': stateful_object_id,
                'stateful_object_content_type_id': stateful_object_content_type_id
            })
        return depended_jobs

    def _set_state(self, instance, new_state):
        """Return a Job or None if the object is already in new_state"""
        from configure.models import StatefulObject
        assert(isinstance(instance, StatefulObject))

        # Work out the eventual states (and which writelock'ing job to depend on to
        # ensure that state) from all non-'complete' jobs in the queue

        self.expected_states = {}
        # TODO: find out how to do a DB query that just gives us the latest WL for
        # each locked_item (same result for less iterations of this loop)
        from configure.models import StateWriteLock
        from django.db.models import Q
        for wl in StateWriteLock.objects.filter(~Q(job__state = 'complete')).order_by('id'):
            self.expected_states[wl.locked_item] = wl.end_state

        if new_state == self.get_expected_state(instance):
            return None

        self.deps = set()
        self.edges = set()
        self.emit_transition_deps(Transition(
            instance,
            self.get_expected_state(instance),
            new_state))

        job_log.debug("Transition %s %s->%s:" % (instance, self.get_expected_state(instance), new_state))
        for d in self.deps:
            job_log.debug("  dep %s" % (d,))
        for e in self.edges:
            job_log.debug("  edge [%s]->[%s]" % (e))

        def sort_graph(objects, edges):
            """Sort items in a graph by their longest path from a leaf.  Items
               at the start of the result are the leaves.  Roots come last."""
            object_edges = defaultdict(list)
            for e in edges:
                parent, child = e
                object_edges[parent].append(child)

            leaf_distance_cache = {}

            def leaf_distance(obj, depth = 0, hops = 0):
                if obj in leaf_distance_cache:
                    return leaf_distance_cache[obj] + hops

                depth = depth + 1
                #print " " * depth + "leaf_distance %s %s" % (obj, hops)
                max_child_hops = hops
                for child in object_edges[obj]:
                    child_hops = leaf_distance(child, depth, hops + 1)
                    max_child_hops = max(child_hops, max_child_hops)

                leaf_distance_cache[obj] = max_child_hops - hops

                return max_child_hops

            object_leaf_distances = []
            for o in objects:
                object_leaf_distances.append((o, leaf_distance(o)))

            object_leaf_distances.sort(lambda x, y: cmp(x[1], y[1]))
            return [obj for obj, ld in object_leaf_distances]

        # XXX
        # VERY IMPORTANT: this sort is what gives us the following rule:
        #  The order of the rows in the Job table corresponds to the order in which
        #  the jobs would run (including accounting for dependencies) in the absence
        #  of parallelism.
        # XXX
        self.deps = sort_graph(self.deps, self.edges)

        jobs = {}
        # Important: the Job must not land in the database until all
        # its dependencies and locks are in.
        with transaction.commit_on_success():
            for d in self.deps:
                job = d.to_job()
                print "job.__class__ = %s" % job.__class__
                job.save()
                job.create_locks()
                job.create_dependencies()
                jobs[d] = job

        from configure.models import Job
        Job.run_next()

    def emit_transition_deps(self, transition):
        if transition in self.deps:
            return transition

        job_log.debug("emit_transition_deps: %s %s->%s" % (transition.stateful_object, transition.old_state, transition.new_state))

        # E.g. for 'unformatted'->'registered' for a ManagedTarget we
        # would get ['unformatted', 'formatted', 'registered']
        route = transition.stateful_object.get_route(transition.old_state, transition.new_state)
        job_log.debug("emit_transition_deps: route %s" % (route,))

        # Add to self.deps and self.edges for each step in the route
        prev = None
        for i in range(0, len(route) - 1):
            dep_transition = Transition(transition.stateful_object, route[i], route[i + 1])
            self.deps.add(dep_transition)
            self.collect_dependencies(dep_transition)
            if prev:
                self.edges.add((dep_transition, prev))
            prev = dep_transition

        return prev

    def collect_dependencies(self, root_transition):
        # What is explicitly required for this state transition?
        transition_deps = root_transition.to_job().get_deps()
        for dependency in transition_deps.all():
            from configure.lib.job import DependOn
            assert(isinstance(dependency, DependOn))
            old_state = self.get_expected_state(dependency.stateful_object)
            if not old_state in dependency.acceptable_states:
                dep_transition = self.emit_transition_deps(Transition(
                        dependency.stateful_object,
                        old_state,
                        dependency.preferred_state))
                self.edges.add((root_transition, dep_transition))

        # What will statically be required in our new state?
        stateful_deps = root_transition.stateful_object.get_deps(root_transition.new_state)
        for dependency in stateful_deps.all():
            # When we start running it will be in old_state
            old_state = self.get_expected_state(dependency.stateful_object)
            # Is old_state not what we want?
            if not old_state in dependency.acceptable_states:
                # Emit some transitions to get depended_on into depended_state
                dep_transition = self.emit_transition_deps(Transition(
                        dependency.stateful_object,
                        old_state,
                        dependency.preferred_state))
                # Record that root_dep depends on depended_on making it into depended_state
                self.edges.add((root_transition, dep_transition))

        # What was depending on our old state?
        # Iterate over all objects which *might* depend on this one
        for dependent in root_transition.stateful_object.get_dependent_objects():
            # What state do we expect the dependent to be in?
            # FIXME: expected_state tells us the state at the start of a _set_state run,
            # not the state when root_transition is going to happen, we should have been
            # recording a stack of transitions on the way to this point in order to know
            # the true expected state prior to root_transition.
            dependent_state = self.get_expected_state(dependent)
            for dependency in dependent.get_deps(dependent_state).all():
                if dependency.stateful_object == root_transition.stateful_object \
                        and not root_transition.new_state in dependency.acceptable_states:
                    assert dependency.fix_state != None, "A reverse dependency must provide a fix_state: %s in state %s depends on %s in state %s" % (dependent, dependent_state, root_transition.stateful_object, dependency.acceptable_states)
                    job_log.debug("Reverse dependency: %s required %s to be in state %s, fixing by setting it to state %s" % (dependent, root_transition.stateful_object, dependency.acceptable_states, dependency.fix_state))
                    dep_transition = self.emit_transition_deps(Transition(
                            dependent,
                            dependent_state, dependency.fix_state))
                    self.edges.add((root_transition, dep_transition))
