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
    def get_transition_job(self, instance, new_state):
        klass = instance.__class__
        old_state = instance.state
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


        try:
            job_klass = self.transition_map[klass][(old_state, new_state)]
            return job_klass(instance)
        except KeyError:
            print "Cannot find transition %s->%s for %s" % (old_state, new_state, klass)
            raise RuntimeError()

    def __init__(self):
        from configure.tasks import StateChangeJob, state_change_job_classes
        from configure.models import StatefulObject

        # Map of StatefulObject subclass to map of
        # (oldstate, newstate) to StateChangeJob subclass
        self.transition_map = {}

        # Map of statefulobject subclass to map of 
        # (oldstate) to list of possible newstates
        self.transition_options_map = {}

        self.stateful_object_classes = subclasses(StatefulObject)

        self.transition_map = defaultdict(dict)
        self.transition_options_map = defaultdict(lambda : defaultdict(list)) 

        for c in state_change_job_classes:
            statefulobject, oldstate, newstate = c.state_transition
            self.transition_map[statefulobject][(oldstate,newstate)] = c
            self.transition_options_map[statefulobject][oldstate].append(newstate)

    def set_state(self, instance, new_state):
        from configure.models import StatefulObject
        assert(isinstance(instance, StatefulObject))
        transition_job = self.get_transition_job(instance, new_state)
        dependencies = self.collect_dependencies(transition_job, new_state)
        print dependencies

    def collect_dependencies(self, root_job, new_state):
        deps = []
        # What is explicitly required for this state transition?
        transition_deps = root_job.get_deps()
        for stateful_object, required_state in transition_deps:
            if stateful_object.state != required_state:
                print "Transition %s required %s in state %s from state %s" % (root_job, stateful_object, required_state, stateful_object.state)
                deps.append((stateful_object, required_state))
                job = self.get_transition_job(stateful_object, required_state)
                deps.extend(self.collect_dependencies(job, required_state))
            
        # What will statically be required in our new state?
        stateful_deps = root_job.stateful_object.get_deps(new_state)
        for depended_on, depended_state, fix_state in stateful_deps:
            if depended_on.state != depended_state:
                print "New state requires %s in state %s from state %s" % (depended_on, depended_state, depended_on.state)
                deps.append((depended_on, depended_state))
                job = self.get_transition_job(depended_on, depended_state)
                deps.extend(self.collect_dependencies(job, depended_state))

        # What was depending on our old state?
        for klass in self.stateful_object_classes:
            for instance in klass.objects.all():
                instance_deps = instance.get_deps()
                for depended_on, depended_state, fix_state in instance_deps:
                    if depended_on == root_job.stateful_object:
                        print "%s depended on %s" % (instance, root_job.stateful_object)
                        if depended_state != new_state:
                            print "%s doesn't like new state %s" % (instance, new_state)
                            deps.append((instance, fix_state))
                            job = self.get_transition_job(instance, fix_state)
                            deps.extend(self.collect_dependencies(job, fix_state))
      
        return deps
