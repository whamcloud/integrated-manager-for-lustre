#!/usr/bin/env python

from collections_24 import defaultdict

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
        from configure.models import Job
        from configure.lib.job import StateChangeJob
        from django.db.models import Q
        locked_objects = set()
        for job in Job.objects.filter(~Q(state = 'complete')):
            if isinstance(job, StateChangeJob):
                locked_objects.add(job.get_stateful_object())

        if stateful_object in locked_objects:
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
        recurse(klass, stateful_object.state)

        klass = self.stateful_object_class(stateful_object)
        #transition_classes = self.transition_options_map[klass][stateful_object.state]
        return [
                {"state": tc.state_transition[2],
                "verb": tc.state_verb} for tc in available_jobs]

    def set_state(self, instance, new_state):
        from configure.models import StatefulObject
        assert(isinstance(instance, StatefulObject))
        if new_state == instance.state:
            raise RuntimeError("already in state %s" % new_state)


        self.deps = set()
        self.edges = set()
        root_dep = self.emit_transition_deps(instance, instance.state, new_state)

        from settings import DEBUG
        if DEBUG:
            for e in self.edges:
                for i in e:
                    if not i in self.deps:
                        print "EDGE parent %s has no dep in %s!" % (i, e)
                        raise RuntimeError()

        jobs = {}
        # We enter a transaction so that no jobs can be started
        # before we've finished wiring up dependencies
        from django.db import transaction
        # FIXME: what happens if we're already in a transaction from a view?
        @transaction.commit_on_success
        def instantiate_jobs():
            from django.db.models import Q
            from configure.models import Job
            incomplete_jobs = Job.objects.filter(~Q(state = 'complete'))
            for job in incomplete_jobs:
                from configure.lib.job import StateChangeJob
                if isinstance(job, StateChangeJob):
                    old_state, new_state = job.state_transition[1:3]
                    dep = (job.get_stateful_object().downcast(), old_state, new_state)

                    print "existing job %s->%s" % (dep, job)
                    jobs[dep] = job

            for d in self.deps:
                if not d in jobs:
                    job = self.dep_to_job(d)
                    job.save()
                    jobs[d] = job
                else:
                    print "recognised existing job %s for dep %s" % (jobs[d], d)
            for e in self.edges:
                parent_dep, child_dep = e
                parent = jobs[parent_dep]
                child = jobs[child_dep]
                parent.dependencies.add(child)

        instantiate_jobs()

        from configure.models import Job
        Job.run_next()

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
                for i in range(0, len(route) - 1):
                    a = route[i]
                    b = route[i + 1]
                    dep = (instance, a, b)
                    self.deps.add(dep)
                    self.collect_dependencies(dep)
                    if prev:
                        self.edges.add((dep, prev))
                    prev = dep

                return prev

            raise RuntimeError()

    def collect_dependencies(self, root_dep):
        # What is explicitly required for this state transition?
        transition_deps = self.dep_to_job(root_dep).get_deps()
        for stateful_object, required_state in transition_deps:
            if stateful_object.state != required_state:
                dep = self.emit_transition_deps(stateful_object, stateful_object.state, required_state)
                self.edges.add((root_dep, dep))
            
        # What will statically be required in our new state?
        stateful_deps = root_dep[0].get_deps(root_dep[2])
        for depended_on, depended_state, fix_state in stateful_deps:
            if depended_on.state != depended_state:
                dep = self.emit_transition_deps(depended_on, depended_on.state, depended_state)
                self.edges.add((root_dep, dep))

        # What was depending on our old state?
        for klass in self.stateful_object_classes:
            for instance in klass.objects.all():
                instance_deps = instance.get_deps()
                for depended_on, depended_state, fix_state in instance_deps:
                    if depended_on == root_dep[0]:
                        if depended_state != root_dep[2]:
                            dep = self.emit_transition_deps(instance, instance.state, fix_state)
                            self.edges.add((root_dep, dep))
