#!/usr/bin/env python

from collections_24 import defaultdict

from logging import getLogger, FileHandler, DEBUG
getLogger('Job').setLevel(DEBUG)
getLogger('Job').addHandler(FileHandler("Job.log"))

def subclasses(obj):
    sc_recr = []
    for sc_obj in obj.__subclasses__():
        sc_recr.append(sc_obj)
        for sc in subclasses(sc_obj):
            sc_recr.append(sc)
    return sc_recr

class StateManager(object):
    def stateful_object_class(self, instance):
        klass = instance.__class__
        # If e.g. klass is ManagedMgs and we have transitions
        # defined for ManagedTarget, then we have to do a more
        # complex lookup
        if not klass in self.transition_map.keys():
            found = False
            for statefulobject_klass in self.transition_map.keys():
                if issubclass(klass, statefulobject_klass):
                    klass = statefulobject_klass
                    found = True
                    break
            if not found:
                raise RuntimeError()

        return klass

    def __init__(self):
        from configure.lib.job import StateChangeJob
        from configure.models import StatefulObject

        # Map of StatefulObject subclass to map of
        # (oldstate, newstate) to StateChangeJob subclass
        self.transition_map = {}

        # Map of statefulobject subclass to map of 
        # (oldstate) to list of possible newstates
        self.transition_options_map = {}

        self.stateful_object_classes = subclasses(StatefulObject)
        state_change_job_classes = subclasses(StateChangeJob)

        self.transition_map = defaultdict(dict)
        self.transition_options_map = defaultdict(lambda : defaultdict(list)) 

        for c in state_change_job_classes:
            statefulobject, oldstate, newstate = c.state_transition
            self.transition_map[statefulobject][(oldstate,newstate)] = c
            self.transition_options_map[statefulobject][oldstate].append(c)

    def available_transitions(self, stateful_object):
        # If the object is subject to an incomplete StateChangeJob
        # then don't offer any other transitions.
        # TODO: extend this to include 'state locking' 
        from configure.models import Job, StateLock
        from configure.lib.job import StateChangeJob
        from django.db.models import Q

        # We don't advertise transitions for anything which is currently
        # locked by an incomplete job.  We could alternatively advertise
        # which jobs would actually be legal to add by skipping this check and
        # using get_expected_state in place of .state below.
        active_locks = StateLock.filter_by_locked_item(stateful_object).filter(~Q(job__state = 'complete')).count()
        if active_locks > 0:
            return []

        available_jobs = set()
        seen_states = set()
        def recurse(klass, initial_state, explore_job = None):
            if explore_job == None:
                explore_state = initial_state
            elif explore_job.state_transition[2] == initial_state:
                return
            else:
                available_jobs.add(explore_job)
                explore_state = explore_job.state_transition[2]

            if explore_state in seen_states:
                return
            seen_states.add(explore_state)
            for next_state in self.transition_options_map[klass][explore_state]:
                recurse(klass, initial_state, next_state)

        klass = self.stateful_object_class(stateful_object)
        # TODO: use expected_state here if you want to advertise 
        # what jobs can really be added
        recurse(klass, stateful_object.state)

        klass = self.stateful_object_class(stateful_object)
        #transition_classes = self.transition_options_map[klass][stateful_object.state]
        return [
                {"state": tc.state_transition[2],
                "verb": tc.state_verb} for tc in available_jobs]

    def get_expected_state(self, stateful_object_instance):
        try:
            return self.expected_states[stateful_object_instance]
        except KeyError:
            return stateful_object_instance.state

    @classmethod
    def notify_state(cls, instance, new_state, from_states):
        """from_states: list of states it's valid to transition from"""
        if not instance.state in from_states:
            return

        from django.db.models import Q
        from configure.models import StateLock
        from configure.models import StatefulObject
        assert(isinstance(instance, StatefulObject))
        if new_state != instance.state:
            outstanding_locks = StateLock.filter_by_locked_item(instance).filter(~Q(job__state = 'complete')).count()
            if outstanding_locks == 0:
                getLogger('Job').info("notify_state: Updating state of item %d (%s) to %s" % (instance.id, instance, new_state))
                # TODO: for concurrency, should insert this state change as a job
                instance.state = new_state
                instance.save()

    def set_state(self, instance, new_state):
        """Return a Job or None if the object is already in new_state"""
        from configure.models import StatefulObject
        assert(isinstance(instance, StatefulObject))
        if new_state == instance.state:
            return None

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
        root_dep = self.emit_transition_deps(
                instance,
                self.get_expected_state(instance),
                new_state)

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
                
                leaf_distance_cache[obj] = max_child_hops - hops;

                return max_child_hops

            object_leaf_distances = []
            for o in objects:
                object_leaf_distances.append((o, leaf_distance(o)))

            object_leaf_distances.sort(lambda x,y: cmp(x[1], y[1]))
            return [obj for obj, ld in object_leaf_distances]

        # XXX
        # VERY IMPORTANT: this sort is what gives us the following rule:
        #  The order of the rows in the Job table corresponds to the order in which
        #  the jobs would run (including accounting for dependecies) in the absence 
        #  of parallelism.
        # XXX
        self.deps = sort_graph(self.deps, self.edges)

        jobs = {}
        # Important: the Job must not land in the database until all
        # its dependencies and locks are in.
        from django.db import transaction
        @transaction.commit_on_success
        def instantiate_jobs():
            for d in self.deps:
                job = self.dep_to_job(d)
                job.save()
                job.create_locks()
                job.create_dependencies()
                jobs[d] = job

        instantiate_jobs()

        from django.db import transaction
        transaction.commit()
        from configure.models import Job
        Job.run_next()

        # FIXME RACE! 
        # If a job completes around the time we insert a new job which 
        # depends on the completing job, then we might add a job with a 
        # dependency count of 1, but the completing job may not see
        # our new job to increment the dependency count on it.

        return jobs[root_dep]

    def dep_to_job(self, dep):
        instance, old_state, new_state = dep
        klass = self.stateful_object_class(instance)
        job_klass = self.transition_map[klass][(old_state, new_state)]
        stateful_object_attr = job_klass.stateful_object
        kwargs = {stateful_object_attr: instance}
        return job_klass(**kwargs)

    def emit_transition_deps(self, instance, old_state, new_state):
        if (instance, old_state, new_state) in self.deps:
            return (instance, old_state, new_state)
        klass = self.stateful_object_class(instance)

        try:
            job_klass = self.transition_map[klass][(old_state, new_state)]
            dep = (instance, old_state, new_state)
            self.deps.add(dep)
            self.collect_dependencies(dep)
            return dep

        except KeyError:
            # Crude: explore all paths from current state until we find one with
            # the desired state
            class FoundState(Exception):
                def __init__(self, path):
                    self.path = path

            def recurse(stack, klass, initial_state, goal_state, explore_state = None):
                if explore_state == initial_state:
                    return
                if explore_state == None:
                    explore_state = initial_state

                stack.append(explore_state)

                if explore_state == goal_state:
                    raise FoundState(stack)
                for next_state in [tc.state_transition[2] for tc in self.transition_options_map[klass][explore_state]]:
                    recurse(stack, klass, initial_state, goal_state, next_state)

            try:
                recurse([], klass, old_state, new_state)
                raise RuntimeError()
            except FoundState, s:
                route = s.path
                prev = None
                # TODO: this code is ugly and uses the first path it finds: it
                # should be finding the shortest path
                for i in range(0, len(route) - 1):
                    a = route[i]
                    b = route[i + 1]
                    dep = (instance, a, b)
                    self.deps.add(dep)
                    self.collect_dependencies(dep)
                    if prev:
                        self.edges.add((dep, prev))
                    prev = dep

                assert(prev != None)
                return prev

            raise RuntimeError()

    def collect_dependencies(self, root_dep):
        # What is explicitly required for this state transition?
        transition_deps = self.dep_to_job(root_dep).get_deps()
        for stateful_object, required_state in transition_deps:
            old_state = self.get_expected_state(stateful_object)
            if old_state != required_state:
                dep = self.emit_transition_deps(stateful_object, old_state, required_state)
                self.edges.add((root_dep, dep))
            
        # What will statically be required in our new state?
        stateful_deps = root_dep[0].get_deps(root_dep[2])
        # For everything we depend on
        for depended_on, depended_state, fix_state in stateful_deps:
            # When we start running it will be in old_state
            old_state = self.get_expected_state(depended_on)
            # Is old_state not what we want?
            if old_state != depended_state:
                # Emit some transitions to get depended_on into depended_state
                dep = self.emit_transition_deps(depended_on, old_state, depended_state)
                # Record that root_dep depends on depended_on making it into depended_state
                self.edges.add((root_dep, dep))

        # What was depending on our old state?
        for klass in self.stateful_object_classes:
            for instance in klass.objects.all():
                # FIXME: this is a bit broken, this 'expected state' is at the start
                # of all jobs in this set_state call, but we should be querying 
                # the expected state right before this particular root_dep
                instance_state = self.get_expected_state(instance)
                instance_deps = instance.get_deps(instance_state)
                # This other guy depended on...
                for depended_on, depended_state, fix_state in instance_deps:
                    # He depended on the root_dep object in a state other than
                    # what we're about to put it into: we must change his state
                    # to allow root_dep to transition
                    if depended_on == root_dep[0] and depended_state != root_dep[2]:
                            dep = self.emit_transition_deps(instance, instance_state, fix_state)
                            self.edges.add((root_dep, dep))
