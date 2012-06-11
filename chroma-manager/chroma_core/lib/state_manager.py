#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
import datetime
import json
import traceback
from dateutil import tz
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.query_utils import Q
import sys
from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.job import job_log
from chroma_core.lib.util import all_subclasses
from chroma_core.models.conf_param import ApplyConfParams
from chroma_core.models.host import ConfigureLNetJob, ManagedHost, GetLNetStateJob
from chroma_core.models.jobs import StateChangeJob, Command, StateLock, Job, SchedulingError
from chroma_core.models.target import ManagedMdt, FilesystemMember, ManagedOst, ManagedTarget


class StateManagerClient(object):
    @classmethod
    def command_run_jobs(cls, job_dicts, message):
        from chroma_core.tasks import command_run_jobs
        return command_run_jobs.delay(job_dicts, message)

    @classmethod
    def command_set_state(cls, object_ids, message, run = True):
        from chroma_core.tasks import command_set_state
        return command_set_state.delay(object_ids, message, run)

    @classmethod
    def notify_state(cls, instance, time, new_state, from_states):
        """from_states: list of states it's valid to transition from.  This lets
           the audit code safely update the state of e.g. a mount it doesn't find
           to 'unmounted' without risking incorrectly transitioning from 'unconfigured'"""
        if instance.state in from_states and instance.state != new_state:
            job_log.info("Enqueuing notify_state %s %s->%s at %s" % (instance, instance.state, new_state, time))
            from chroma_core.tasks import notify_state
            return notify_state.delay(
                instance.content_type.natural_key(),
                instance.id,
                time,
                new_state,
                from_states)

    @classmethod
    def complete_job(cls, job_id):
        from chroma_core.tasks import complete_job
        return complete_job.delay(job_id)

    @classmethod
    def available_transitions(cls, stateful_object):
        return StateManager().available_transitions(stateful_object)

    @classmethod
    def available_jobs(cls, stateful_object):
        return StateManager().available_jobs(stateful_object)

    @classmethod
    def get_transition_consequences(cls, stateful_object, new_state):
        return StateManager().get_transition_consequences(stateful_object, new_state)


class LockCache(object):
    instance = None
    enable = True

    def __init__(self):
        self.write_locks = []
        self.write_by_item = defaultdict(list)
        self.read_locks = []
        self.read_by_item = defaultdict(list)
        self.all_by_job = defaultdict(list)
        self.all_by_item = defaultdict(list)

        for job in Job.objects.filter(~Q(state = 'complete')):
            if job.locks_json:
                locks = json.loads(job.locks_json)
                for lock in locks:
                    self._add(StateLock.from_dict(job, lock))

    @classmethod
    def clear(cls):
        cls.instance = None

    @classmethod
    def add(cls, lock):
        cls.getInstance()._add(lock)

    def _add(self, lock):
        if lock.write:
            self.write_locks.append(lock)
            self.write_by_item[lock.locked_item].append(lock)
        else:
            self.read_locks.append(lock)
            self.read_by_item[lock.locked_item].append(lock)

        self.all_by_job[lock.job].append(lock)
        self.all_by_item[lock.locked_item].append(lock)

    @classmethod
    def getInstance(cls):
        if not cls.instance:
            cls.instance = LockCache()
        return cls.instance

    @classmethod
    def get_by_job(cls, job):
        return cls.getInstance().all_by_job[job]

    @classmethod
    def get_all(cls, locked_item):
        return cls.getInstance().all_by_item[locked_item]

    @classmethod
    def get_latest_write(cls, locked_item, not_job = None):
        try:
            if not_job != None:
                return sorted([l for l in cls.getInstance().write_by_item[locked_item] if l.job != not_job], lambda a, b: cmp(a.job.id, b.job.id))[-1]
            else:
                return sorted(cls.getInstance().write_by_item[locked_item], lambda a, b: cmp(a.job.id, b.job.id))[-1]
        except IndexError:
            return None

    @classmethod
    def get_read_locks(cls, locked_item, after, not_job):
        return [x for x in cls.getInstance().read_by_item[locked_item] if after <= x.job.id and x.job != not_job]

    @classmethod
    def get_write(cls, locked_item):
        return cls.getInstance().write_by_item[locked_item]

    @classmethod
    def get_by_locked_item(cls, item):
        return cls.getInstance().all_by_item[item]

    @classmethod
    def get_write_by_locked_item(cls):
        result = {}
        for locked_item, locks in cls.getInstance().write_by_item.items():
            if locks:
                result[locked_item] = sorted(locks, lambda a, b: cmp(a.job.id, b.job.id))[-1]
        return result


class DepCache(object):
    instance = None
    enable = True

    @classmethod
    def getInstance(cls):
        if not cls.instance:
            cls.instance = DepCache()
        return cls.instance

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.cache = {}

    @classmethod
    def clear(cls):
        cls.instance = None

    def _get(self, obj, state):
        if state:
            return obj.get_deps(state)
        else:
            return obj.get_deps()

    def get(self, obj, state = None):
        from chroma_core.models import StatefulObject
        if state == None and isinstance(obj, StatefulObject):
            state = obj.state

        if not self.enable:
            return self._get(obj, state)

        if state:
            key = (obj, state)
        else:
            key = obj

        try:
            v = self.cache[key]
            self.hits += 1

            return v
        except KeyError:
            self.cache[key] = self._get(obj, state)
            self.misses += 1
            return self.cache[key]


def get_deps(obj, state = None):
    return DepCache.getInstance().get(obj, state)


class Transition(object):
    def __init__(self, stateful_object, old_state, new_state):
        self.stateful_object = stateful_object
        self.old_state = old_state
        self.new_state = new_state

    def __str__(self):
        return "%s/%s %s->%s" % (self.stateful_object.__class__, self.stateful_object.id, self.old_state, self.new_state)

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.stateful_object.__hash__(), self.old_state, self.new_state))

    def to_job(self):
        job_klass = self.stateful_object.get_job_class(self.old_state, self.new_state)
        stateful_object_attr = job_klass.stateful_object
        kwargs = {stateful_object_attr: self.stateful_object, 'old_state': self.old_state}
        return job_klass(**kwargs)


class StateManager(object):
    def __init__(self):
        DepCache.clear()
        LockCache.clear()
        ObjectCache.clear()

    def available_jobs(self, instance):
        # If the object is subject to an incomplete Job
        # then don't offer any actions
        if LockCache.get_latest_write(instance) > 0:
            return []

        from chroma_core.models import AdvertisedJob

        available_jobs = []
        for aj in all_subclasses(AdvertisedJob):
            if not aj.plural:
                for class_name in aj.classes:
                    ct = ContentType.objects.get_by_natural_key('chroma_core', class_name)
                    klass = ct.model_class()
                    if isinstance(instance, klass):
                        if aj.can_run(instance):
                            available_jobs.append({
                                'verb': aj.verb,
                                'confirmation': aj.get_confirmation(instance),
                                'class_name': aj.__name__,
                                'args': aj.get_args(instance)})

        return available_jobs

    def available_transitions(self, stateful_object):
        """Return a list states to which the object can be set from
           its current state, or None if the object is currently
           locked by a Job"""
        if hasattr(stateful_object, 'content_type'):
            stateful_object = stateful_object.downcast()

        # We don't advertise transitions for anything which is currently
        # locked by an incomplete job.  We could alternatively advertise
        # which jobs would actually be legal to add by skipping this check and
        # using get_expected_state in place of .state below.
        if LockCache.get_latest_write(stateful_object):
            return []

        # XXX: could alternatively use expected_state here if you want to advertise
        # what jobs can really be added (i.e. advertise transitions which will
        # be available when current jobs are complete)
        #from_state = self.get_expected_state(stateful_object)
        from_state = stateful_object.state
        available_states = stateful_object.get_available_states(from_state)
        transitions = []
        for to_state in available_states:
            verb = stateful_object.get_verb(from_state, to_state)
            # NB: a None verb means its an internal transition that shouldn't be advertised
            if verb != None:
                transitions.append({"state": to_state, "verb": verb})

        return transitions

    def _completion_hooks(self, changed_item, command = None):
        """
        :param command: If set, any created jobs are added
        to this command object.
        """
        if hasattr(changed_item, 'content_type'):
            changed_item = changed_item.downcast()

        if isinstance(changed_item, FilesystemMember):
            fs = changed_item.filesystem
            members = list(ManagedMdt.objects.filter(filesystem = fs)) + list(ManagedOst.objects.filter(filesystem = fs))
            states = set([t.state for t in members])
            now = datetime.datetime.utcnow().replace(tzinfo = tz.tzutc())
            if not fs.state == 'available' and changed_item.state in ['mounted', 'removed'] and states == set(['mounted']):
                self.notify_state(ContentType.objects.get_for_model(fs).natural_key(), fs.id, now, 'available', ['stopped', 'unavailable'])
            if changed_item.state == 'unmounted' and fs.state != 'stopped' and states == set(['unmounted']):
                self.notify_state(ContentType.objects.get_for_model(fs).natural_key(), fs.id, now, 'stopped', ['stopped', 'unavailable'])
            if changed_item.state == 'unmounted' and fs.state == 'available' and states != set(['mounted']):
                self.notify_state(ContentType.objects.get_for_model(fs).natural_key(), fs.id, now, 'unavailable', ['available'])

        if isinstance(changed_item, ManagedHost):
            if changed_item.state == 'lnet_up' and changed_item.lnetconfiguration.state != 'nids_known':
                if not ConfigureLNetJob.objects.filter(~Q(state = 'complete'), lnet_configuration = changed_item.lnetconfiguration).count():
                    job = ConfigureLNetJob(lnet_configuration = changed_item.lnetconfiguration, old_state = 'nids_unknown')
                    if not command:
                        command = Command.objects.create(message = "Configuring LNet on %s" % changed_item)
                    self.add_jobs([job], command)

            if changed_item.state == 'configured':
                if not GetLNetStateJob.objects.filter(~Q(state = 'complete'), host = changed_item).count():
                    job = GetLNetStateJob(host = changed_item)
                    if not command:
                        command = Command.objects.create(message = "Getting LNet state for %s" % changed_item)
                    self.add_jobs([job], command)

        if isinstance(changed_item, ManagedTarget):
            if isinstance(changed_item, FilesystemMember):
                mgs = changed_item.filesystem.mgs
            else:
                mgs = changed_item

            if mgs.conf_param_version != mgs.conf_param_version_applied:
                if not ApplyConfParams.objects.filter(~Q(state = 'complete'), mgs = mgs).count():
                    job = ApplyConfParams(mgs = mgs)
                    if get_deps(job).satisfied():
                        if not command:
                            command = Command.objects.create(message = "Updating configuration parameters on %s" % mgs)
                        self.add_jobs([job], command)

    def notify_state(self, content_type, object_id, notification_time, new_state, from_states):
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
            if not len(LockCache.get_by_locked_item(instance)):
                modified_at = instance.state_modified_at
                modified_at = modified_at.replace(tzinfo = tz.tzutc())

                if notification_time > modified_at:
                    # No jobs lock this object, go ahead and update its state
                    job_log.info("notify_state: Updating state of item %s (%s) from %s to %s" % (instance.id, instance, instance.state, new_state))
                    instance.set_state(new_state)

                    # FIXME: should check the new state against reverse dependencies
                    # and apply any fix_states
                    self._completion_hooks(instance)
                else:
                    job_log.info("notify_state: Dropping update of %s (%s) %s->%s because it has been updated since" % (instance.id, instance, instance.state, new_state))
                    pass

    def get_expected_state(self, stateful_object_instance):
        try:
            return self.expected_states[stateful_object_instance]
        except KeyError:
            return stateful_object_instance.state

    def complete_job(self, job_id):
        from chroma_core.models import Job

        job = Job.objects.get(pk = job_id)
        if job.state == 'completing':
            with transaction.commit_on_success():
                job.state = 'complete'
                job.save()
        else:
            assert job.state == 'complete'

        # FIXME: we use cancelled to indicate a job which didn't run
        # because its dependencies failed, and also to indicate a job
        # that was deliberately cancelled by the user.  We should
        # distinguish so that opportunistic retry doesn't happen when
        # the user has explicitly cancelled something.
        job = job.downcast()

        if job.locks_json:
            try:
                command = Command.objects.filter(jobs = job, complete = False)[0]
            except IndexError:
                job_log.warning("Job %s: No incomplete command while completing" % job_id)
                command = None
            for lock in json.loads(job.locks_json):
                if lock['write']:
                    lock = StateLock.from_dict(job, lock)
                    try:
                        self._completion_hooks(lock.locked_item, command)
                    except Exception:
                        job_log.error("Error in completion hooks: %s" % '\n'.join(traceback.format_exception(*(sys.exc_info()))))

        for command in Command.objects.filter(jobs = job):
            command.check_completion()

    def add_jobs(self, jobs, command):
        """Add a job, and any others which are required in order to reach its prerequisite state"""
        # Important: the Job must not be committed until all
        # its dependencies and locks are in.
        assert transaction.is_managed()

        for job in jobs:
            for dependency in get_deps(job).all():
                if not dependency.satisfied():
                    job_log.info("add_jobs: setting required dependency %s %s" % (dependency.stateful_object, dependency.preferred_state))
                    self.set_state(dependency.get_stateful_object(), dependency.preferred_state, command)
            job_log.info("add_jobs: done checking dependencies")
            locks = job.create_locks()
            for l in locks:
                LockCache.add(l)
            self._create_dependencies(job)
            job.save()
            job_log.info("add_jobs: created Job %s (%s)" % (job.pk, job.description()))
            command.jobs.add(job)

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
        from chroma_core.models import StatefulObject
        assert(isinstance(instance, StatefulObject))

        self.expected_states = {}
        self.deps = set()
        self.edges = set()
        self.emit_transition_deps(Transition(
            instance,
            self.get_expected_state(instance),
            new_state))

        #job_log.debug("Transition %s %s->%s:" % (instance, self.get_expected_state(instance), new_state))
        #for d in self.deps:
        #    job_log.debug("  dep %s" % (d,))
        #for e in self.edges:
        #    job_log.debug("  edge [%s]->[%s]" % (e))
        self.deps = self._sort_graph(self.deps, self.edges)

        depended_jobs = []
        transition_job = None
        for d in self.deps:
            job = d.to_job()
            if isinstance(job, StateChangeJob):
                from django.contrib.contenttypes.models import ContentType
                so = getattr(job, job.stateful_object)
                stateful_object_id = so.pk
                stateful_object_content_type_id = ContentType.objects.get_for_model(so).pk
            else:
                stateful_object_id = None
                stateful_object_content_type_id = None

            description = {
                'class': job.__class__.__name__,
                'requires_confirmation': job.get_requires_confirmation(),
                'confirmation_prompt': job.get_confirmation_string(),
                'description': job.description(),
                'stateful_object_id': stateful_object_id,
                'stateful_object_content_type_id': stateful_object_content_type_id
            }

            if d == self.deps[-1]:
                transition_job = description
            else:
                depended_jobs.append(description)

        return {'transition_job': transition_job, 'dependency_jobs': depended_jobs}

    def _create_dependencies(self, job):
        """Examine overlaps between self's statelocks and those of
           earlier jobs which are still pending, and generate wait_for
           dependencies when we have a write lock and they have a read lock
           or generate depend_on dependencies when we have a read or write lock and
           they have a write lock"""
        wait_fors = set()
        for lock in LockCache.get_by_job(job):
            job_log.debug("Job %s: %s" % (job, lock))
            if lock.write:
                wl = lock
                # Depend on the most recent pending write to this stateful object,
                # trust that it will have depended on any before that.
                prior_write_lock = LockCache.get_latest_write(wl.locked_item, not_job = job)
                if prior_write_lock:
                    if wl.begin_state and prior_write_lock.end_state:
                        assert (wl.begin_state == prior_write_lock.end_state), ("%s locks %s in state %s but previous %s leaves it in state %s" % (job, wl.locked_item, wl.begin_state, prior_write_lock.job, prior_write_lock.end_state))
                    job_log.debug("Job %s:   pwl %s" % (job, prior_write_lock))
                    wait_fors.add(prior_write_lock.job.id)
                    # We will only wait_for read locks after this write lock, as it
                    # will have wait_for'd any before it.
                    read_barrier_id = prior_write_lock.job.id
                else:
                    read_barrier_id = 0

                # Wait for any reads of the stateful object between the last write and
                # our position.
                prior_read_locks = LockCache.get_read_locks(wl.locked_item, after = read_barrier_id, not_job = job)
                for i in prior_read_locks:
                    job_log.debug("Job %s:   prl %s" % (job, i))
                    wait_fors.add(i.job.id)
            else:
                rl = lock
                prior_write_lock = LockCache.get_latest_write(rl.locked_item, not_job = job)
                if prior_write_lock:
                    # See comment by locked_state in StateReadLock
                    wait_fors.add(prior_write_lock.job.id)
                job_log.debug("Job %s:   pwl2 %s" % (job, prior_write_lock))

        wait_fors = list(wait_fors)
        if wait_fors:
            job.wait_for_json = json.dumps(wait_fors)

    def _sort_graph(self, objects, edges):
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

    def set_state(self, instance, new_state, command):
        """Return a Job or None if the object is already in new_state.
        command_id should refer to a command instance or be None."""

        job_log.info("set_state: %s-%s to state %s" % (instance.__class__, instance.id, new_state))

        DepCache.getInstance()
        LockCache.getInstance()
        ObjectCache.getInstance()

        from chroma_core.models import StatefulObject
        assert(isinstance(instance, StatefulObject))
        if new_state not in instance.states:
            raise SchedulingError("State '%s' is invalid for %s, must be one of %s" % (new_state, instance.__class__, instance.states))

        # Work out the eventual states (and which writelock'ing job to depend on to
        # ensure that state) from all non-'complete' jobs in the queue
        item_to_lock = LockCache.get_write_by_locked_item()
        self.expected_states = dict([(k, v.end_state) for k, v in item_to_lock.items()])

        if new_state == self.get_expected_state(instance):
            if instance.state != new_state:
                # This is a no-op because of an in-progress Job:
                job = LockCache.get_latest_write(instance).job
                command.jobs.add(job)

            command.check_completion()

            # Pick out whichever job made it so, and attach that to the Command
            return None

        self.deps = set()
        self.edges = set()
        self.emit_transition_deps(Transition(
            instance,
            self.get_expected_state(instance),
            new_state))

        # XXX
        # VERY IMPORTANT: this sort is what gives us the following rule:
        #  The order of the rows in the Job table corresponds to the order in which
        #  the jobs would run (including accounting for dependencies) in the absence
        #  of parallelism.
        # XXX
        self.deps = self._sort_graph(self.deps, self.edges)

        #job_log.debug("Transition %s %s->%s:" % (instance, self.get_expected_state(instance), new_state))
        #for e in self.edges:
        #    job_log.debug("  edge [%s]->[%s]" % (e))

        # Important: the Job must not land in the database until all
        # its dependencies and locks are in.
        with transaction.commit_on_success():
            for d in self.deps:
                job_log.debug("  dep %s" % d)
                job = d.to_job()
                locks = job.create_locks()
                job.locks_json = json.dumps([l.to_dict() for l in locks])
                for l in locks:
                    LockCache.add(l)
                self._create_dependencies(job)
                job.save()
                job_log.debug("  dep %s -> Job %s" % (d, job.pk))
                command.jobs.add(job)

            command.save()

    def emit_transition_deps(self, transition, transition_stack = {}):
        if transition in self.deps:
            job_log.debug("emit_transition_deps: %s already scheduled" % (transition))
            return transition
        else:
            job_log.debug("emit_transition_deps: %s" % (transition))
            pass

        # Update our worldview to record that any subsequent dependencies may
        # assume that we are in our new state
        transition_stack = dict(transition_stack.items())
        transition_stack[transition.stateful_object] = transition.new_state
        job_log.debug("Updating transition_stack[%s/%s] = %s" % (transition.stateful_object.__class__, transition.stateful_object.id, transition.new_state))

        # E.g. for 'unformatted'->'registered' for a ManagedTarget we
        # would get ['unformatted', 'formatted', 'registered']
        route = transition.stateful_object.get_route(transition.old_state, transition.new_state)
        job_log.debug("emit_transition_deps: route %s" % (route,))

        # Add to self.deps and self.edges for each step in the route
        prev = None
        for i in range(0, len(route) - 1):
            dep_transition = Transition(transition.stateful_object, route[i], route[i + 1])
            self.deps.add(dep_transition)
            self.collect_dependencies(dep_transition, transition_stack)
            if prev:
                self.edges.add((dep_transition, prev))
            prev = dep_transition

        return prev

    def collect_dependencies(self, root_transition, transition_stack):
        if not hasattr(self, 'cdc'):
            self.cdc = defaultdict(list)
        if root_transition in self.cdc:
            return

        job_log.debug("collect_dependencies: %s" % root_transition)
        # What is explicitly required for this state transition?
        transition_deps = get_deps(root_transition.to_job())
        for dependency in transition_deps.all():
            from chroma_core.lib.job import DependOn
            assert(isinstance(dependency, DependOn))
            old_state = self.get_expected_state(dependency.stateful_object)
            job_log.debug("cd %s/%s %s %s" % (dependency.stateful_object.__class__, dependency.stateful_object.id, old_state, dependency.acceptable_states))

            if not old_state in dependency.acceptable_states:
                dep_transition = self.emit_transition_deps(Transition(
                        dependency.stateful_object,
                        old_state,
                        dependency.preferred_state), transition_stack)
                self.edges.add((root_transition, dep_transition))

        def get_mid_transition_expected_state(object):
            try:
                return transition_stack[object]
            except KeyError:
                return self.get_expected_state(object)

        # What will statically be required in our new state?
        stateful_deps = get_deps(root_transition.stateful_object, root_transition.new_state)
        for dependency in stateful_deps.all():
            if dependency.stateful_object in transition_stack:
                continue
            # When we start running it will be in old_state
            old_state = get_mid_transition_expected_state(dependency.stateful_object)

            # Is old_state not what we want?
            if not old_state in dependency.acceptable_states:
                job_log.debug("new state static requires = %s %s %s" % (dependency.stateful_object, old_state, dependency.acceptable_states))
                # Emit some transitions to get depended_on into depended_state
                dep_transition = self.emit_transition_deps(Transition(
                        dependency.stateful_object,
                        old_state,
                        dependency.preferred_state), transition_stack)
                # Record that root_dep depends on depended_on making it into depended_state
                self.edges.add((root_transition, dep_transition))

        # What was depending on our old state?
        # Iterate over all objects which *might* depend on this one
        for dependent in root_transition.stateful_object.get_dependent_objects():
            if dependent in transition_stack:
                continue
            # What state do we expect the dependent to be in?
            dependent_state = get_mid_transition_expected_state(dependent)
            for dependency in get_deps(dependent, dependent_state).all():
                if dependency.stateful_object == root_transition.stateful_object \
                        and not root_transition.new_state in dependency.acceptable_states:
                    assert dependency.fix_state != None, "A reverse dependency must provide a fix_state: %s in state %s depends on %s in state %s" % (dependent, dependent_state, root_transition.stateful_object, dependency.acceptable_states)
                    job_log.debug("Reverse dependency: %s-%s in state %s required %s to be in state %s (but will be %s), fixing by setting it to state %s" % (
                        dependent, dependent_state, root_transition.stateful_object.__class__,
                        root_transition.stateful_object.id, dependency.acceptable_states, root_transition.new_state,
                        dependency.fix_state))

                    if hasattr(dependency.fix_state, '__call__'):
                        fix_state = dependency.fix_state(root_transition.new_state)
                    else:
                        fix_state = dependency.fix_state

                    dep_transition = self.emit_transition_deps(Transition(
                            dependent,
                            dependent_state, fix_state), transition_stack)
                    self.edges.add((root_transition, dep_transition))

    def command_run_jobs(self, job_dicts, message):
        assert(len(job_dicts) > 0)
        with transaction.commit_on_success():
            jobs = []
            for job in job_dicts:
                job_klass = ContentType.objects.get_by_natural_key('chroma_core', job['class_name'].lower()).model_class()

                m2m_attrs = {}
                for field in job_klass._meta.local_many_to_many:
                    m2m_attrs[field.attname] = field.rel.to

                args = job['args']
                m2m_values = {}
                for k, v in args.items():
                    if k in m2m_attrs:
                        m2m_values[k] = v
                        del args[k]

                # FIXME: I have to save the job to add its m2m
                # fields, but I can't save it until after I've created its
                # precursor jobs (the job ID influences order of run)
                job_instance = job_klass(**args)
                #job_instance.save()
                jobs.append(job_instance)
                #for attr in m2m_attrs.keys():
                ##    m2m_attr = getattr(job_instance, attr)
                #    for id in m2m_values[attr]:
                #        instance = m2m_attrs[attr].objects.get(pk = id)
                #        m2m_attr.add(instance)

            command = Command.objects.create(message = message)
            job_log.debug("command_run_jobs: command %s" % command.id)
            for job in jobs:
                job_log.debug("command_run_jobs:  job %s" % job.id)
            self.add_jobs(jobs, command)
            command.save()

        return command.id

    def command_set_state(self, object_ids, message):
        """object_ids must be a list of 3-tuples of CT natural key, object PK, state"""
        # StateManager.set_state is invoked in an async task for two reasons:
        #  1. At time of writing, StateManager.set_state's logic is not safe against
        #     concurrent runs that might schedule multiple jobs for the same objects.
        #     Submitting to a single-worker queue is a simpler and more efficient
        #     way of serializing than locking the table in the database, as we don't
        #     exclude workers from setting there completion and advancing the queue
        #     while we're scheduling new jobs.
        #  2. Calculating the dependencies of a new state is not trivial, because operation
        #     may have thousands of dependencies (think stopping a filesystem with thousands
        #     of OSTs).  We want views like those that create+format a target to return
        #     snappily.
        #
        #  nb. there is an added bonus that StateManager uses some cached tables
        #      built from introspecting StatefulObject and StateChangeJob classes,
        #      and a long-lived worker process keeps those in memory for you.

        with transaction.commit_on_success():
            command = Command.objects.create(message = message)
            for ct_nk, o_pk, state in object_ids:
                model_klass = ContentType.objects.get_by_natural_key(*ct_nk).model_class()
                instance = model_klass.objects.get(pk = o_pk)
                self.set_state(instance, state, command)

        return command.id
