
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models

CONFIGURE_MODELS = True
from monitor import models as monitor_models
from polymorphic.models import DowncastMetaclass

from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from collections_24 import defaultdict

MAX_STATE_STRING = 32

def _subclasses(obj):
    """Used to introspect all descendents of a class.  Used because metaclasses
       are a PITA when doing multiple inheritance"""
    sc_recr = []
    for sc_obj in obj.__subclasses__():
        sc_recr.append(sc_obj)
        for sc in _subclasses(sc_obj):
            sc_recr.append(sc)
    return sc_recr

class StatefulObject(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True

    state = models.CharField(max_length = MAX_STATE_STRING)
    states = None
    initial_state = None

    reverse_deps = {}

    def __init__(self, *args, **kwargs):
        super(StatefulObject, self).__init__(*args, **kwargs)

        if not self.state:
            self.state = self.initial_state

    def get_deps(self, state = None):
        """Return static dependencies, e.g. a targetmount in state
           mounted has a dependency on a host in state lnet_started but
           can get rid of it by moving to state unmounted"""
        return []

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
                if issubclass(b, StatefulObject):
                    return StatefulObject.so_child(b)

    @classmethod
    def _build_maps(cls):
        """Populate route_map and transition_map attributes by introspection of 
           this class and related StateChangeJob classes.  It is legal to call this
           twice or concurrently."""
        cls = StatefulObject.so_child(cls)

        transition_classes = [s for s in _subclasses(StateChangeJob) if s.state_transition[0] == cls]
        transition_options = defaultdict(list)
        job_class_map = {}
        for c in transition_classes:
            from_state, to_state = c.state_transition[1], c.state_transition[2]
            transition_options[from_state].append(to_state)
            job_class_map[(from_state, to_state)] = c

        transition_map = defaultdict(list)
        route_map = {}
        shortest_routes = []
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
                possible_routes.sort(lambda a,b: cmp(len(a), len(b)))
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

    @classmethod
    def get_available_states(cls, begin_state):
        if not begin_state in cls.states:
            raise RuntimeError("%s not legal state for %s, legal states are %s" % (begin_state, cls, cls.states))

        if not hasattr(cls, 'transition_map'):
            cls._build_maps()

        return cls.transition_map[begin_state]     

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
            for klass in _subclasses(StatefulObject):
                for class_name, lookup_fn in klass.reverse_deps.items():
                    so_class = ContentType.objects.get_by_natural_key('configure', class_name).model_class()
                    reverse_deps_map[so_class].append(lookup_fn)
            StatefulObject.reverse_deps_map = reverse_deps_map

        from itertools import chain
        lookup_fns = StatefulObject.reverse_deps_map[self.__class__]
        querysets = [fn(self) for fn in lookup_fns]
        return chain(*querysets)

class ManagedFilesystem(monitor_models.Filesystem):
    def get_conf_params(self):
        from itertools import chain
        params = chain(self.filesystemclientconfparam_set.all(),self.filesystemglobalconfparam_set.all())
        return ConfParam.get_latest_params(params)

class ManagedTarget(StatefulObject):
    __metaclass__ = DowncastMetaclass
    # unformatted: I exist in theory in the database 
    # formatted: I've been mkfs'd
    # unmounted: I've registered with the MGS, I'm not mounted
    # mounted: I've registered with the MGS, I'm mounted
    # removed: this target no longer exists in real life
    # Additional states needed for 'deactivated'?
    states = ['unformatted', 'formatted', 'unmounted', 'mounted', 'removed']
    initial_state = 'unformatted'

    def get_deps(self, state = None):
        if not state:
            state = self.state
        
        deps = []
        if state == 'mounted':
            for tm in self.targetmount_set.all():
                # TODO: rewrite this dependency to 'at least one targetmount
                # host must have LNET up' such that we will attempt to 
                # bring up LNET on all but not stop unless none succeed.
                deps.append((tm.host.downcast(), 'lnet_up', 'unmounted'))

                # TODO: rewrite this dependency to depend on there being at
                # least one configured targetmount in order to mount a managedtarget
                # and add a dep to teh job for unconfiguring a targetmount to 
                # ensure that this target is down when that happens (but let
                # it come up again if there is at least one remaining targetmount)
                deps.append((tm.downcast(), 'configured', 'unmounted'))

        return deps

class ManagedOst(monitor_models.ObjectStoreTarget, ManagedTarget):
    def get_conf_params(self):
        return ConfParam.get_latest_params(self.ostconfparam_set.all())

    def default_mount_path(self, host):
        counter = 0
        while True:
            candidate = "/mnt/%s/ost%d" % (self.filesystem.name, counter)
            try:
                monitor_models.Mountable.objects.get(host = host, mount_point = candidate)
                counter = counter + 1
            except monitor_models.Mountable.DoesNotExist:
                return candidate

class ManagedMdt(monitor_models.MetadataTarget, ManagedTarget):
    def get_conf_params(self):
        return ConfParam.get_latest_params(self.mdtconfparam_set.all())

    def default_mount_path(self, host):
        return "/mnt/%s/mdt" % self.filesystem.name

class ManagedMgs(monitor_models.ManagementTarget, ManagedTarget):
    conf_param_version = models.IntegerField(default = 0)
    conf_param_version_applied = models.IntegerField(default = 0)

    def default_mount_path(self, host):
        return "/mnt/mgs"

    def set_conf_params(self, params):
        """params is a list of unsaved ConfParam objects"""

        # Obtain a version
        from django.db import transaction
        @transaction.commit_on_success()
        def get_version():
            from django.db.models import F
            ManagedMgs.objects.filter(pk = self.id).update(conf_param_version = F('conf_param_version') + 1)
            return ManagedMgs.objects.get(pk = self.id).conf_param_version

        version = get_version()

        @transaction.commit_on_success()
        def create_params():
            for p in params:
                p.version = version
                p.save()

        create_params()

    def get_conf_params(self):
        return ConfParam.get_latest_params(self.confparam_set.all())

class ManagedHost(monitor_models.Host, StatefulObject):
    states = ['lnet_unloaded', 'lnet_down', 'lnet_up']
    initial_state = 'lnet_unloaded'

class ManagedTargetMount(monitor_models.TargetMount, StatefulObject):
    # unconfigured: I only exist in theory in the database
    # mounted: I am in fstab on the host and mounted
    # unmounted: I am in fstab on the host and unmounted
    states = ['unconfigured', 'configured']
    initial_state = 'unconfigured'

    def __str__(self):
        if self.primary:
            kind_string = "primary"
        elif not self.block_device:
            kind_string = "failover_nodev"
        else:
            kind_string = "failover"

        return "%s:%s:%s" % (self.host, kind_string, self.target)

    def get_deps(self, state = None):
        if not state:
            state = self.state

        deps = []
        if state == 'configured':
            # TODO: depend on target in state unmounted OR mounted
            # in order to get this unconfigured when the target is removed.
            #deps.append(self.target.downcast(), ['mounted', 'unmounted'], 'unconfigured']
            pass
        return deps

    # Reverse dependencies are records of other classes which must check
    # our get_deps when they change state.
    # It tells them how, given an instance of the other class, to find 
    # instances of this class which may depend on it.
    reverse_deps = {
            # We depend on lnet_state
            'ManagedHost': (lambda mh: ManagedTargetMount.objects.filter(host = mh)),
            # We depend on state 'registered'
            'ManagedTarget': (lambda mt: ManagedTargetMount.objects.filter(target = mt)),
            # A TargetMount may depend on other targetmounts for the same target
            'ManagedTargetMount': (lambda mtm: mtm.target.targetmount_set.filter(~Q(pk = mtm.id)))
            }


class StateLock(models.Model):
    __metaclass__ = DowncastMetaclass
    job = models.ForeignKey('Job')

    locked_item_type = models.ForeignKey(ContentType, related_name = 'locked_item')
    locked_item_id = models.PositiveIntegerField()
    locked_item = GenericForeignKey('locked_item_type', 'locked_item_id')

    @classmethod
    def filter_by_locked_item(cls, stateful_object):
        ctype = ContentType.objects.get_for_model(stateful_object)
        return cls.objects.filter(locked_item_type = ctype, locked_item_id = stateful_object.id)

class StateReadLock(StateLock):
    locked_state = models.CharField(max_length = MAX_STATE_STRING)

class StateWriteLock(StateLock):
    begin_state = models.CharField(max_length = MAX_STATE_STRING)
    end_state = models.CharField(max_length = MAX_STATE_STRING)

# Lock is the wrong word really, these objects exist for the lifetime of the Job, 
# to allow 
# All locks depend on the last pending job to write to a stateful object on which
# they hold claim read or write lock.

class Test(models.Model):
    i = models.IntegerField(default = 0)

class Job(models.Model):
    __metaclass__ = DowncastMetaclass

    states = ('pending', 'tasked', 'complete', 'completing', 'cancelling', 'paused')
    state = models.CharField(max_length = 16, default = 'pending')

    errored = models.BooleanField(default = False)
    paused = models.BooleanField(default = False)
    cancelled = models.BooleanField(default = False)

    modified_at = models.DateTimeField(auto_now = True)
    created_at = models.DateTimeField(auto_now_add = True)

    wait_for_count = models.PositiveIntegerField(default = 0)
    wait_for_completions = models.PositiveIntegerField(default = 0)
    wait_for = models.ManyToManyField('Job', symmetrical = False, related_name = 'wait_for_job')

    depend_on_count = models.PositiveIntegerField(default = 0)
    depend_on_completions = models.PositiveIntegerField(default = 0)
    depend_on = models.ManyToManyField('Job', symmetrical = False, related_name = 'depend_on_job')

    task_id = models.CharField(max_length=36, blank = True, null = True)
    def task_state(self):
        from celery.result import AsyncResult
        return AsyncResult(self.task_id).state

    # Set to a step index before that step starts running
    started_step = models.PositiveIntegerField(default = None, blank = True, null = True)
    # Set to a step index when that step has finished and its result is committed
    finished_step = models.PositiveIntegerField(default = None, blank = True, null = True)

    def notify_wait_for_complete(self):
        """Called by a wait_for job to notify that it is complete"""
        from django.db.models import F
        Job.objects.get_or_create(pk = self.id)
        Job.objects.filter(pk = self.id).update(wait_for_completions = F('wait_for_completions')+1)
   
    def notify_depend_on_complete(self):
        """Called by a depend_on job to notify that it is complete"""
        from django.db.models import F
        Job.objects.get_or_create(pk = self.id)
        Job.objects.filter(pk = self.id).update(depend_on_completions = F('depend_on_completions')+1)

    def create_dependencies(self):
        """Examine overlaps between self's statelocks and those of 
           earlier jobs which are still pending, and generate wait_for
           dependencies when we have a write lock and they have a read lock
           or generate depend_on dependencies when we have a read or write lock and
           they have a write lock"""
        from configure.lib.job import job_log

        for lock in self.statelock_set.all():
            if isinstance(lock, StateWriteLock):
                wl = lock
                # Depend on the most recent pending write to this stateful object,
                # trust that it will have depended on any before that.
                try:
                    prior_write_lock = StateWriteLock.filter_by_locked_item(wl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).latest('id')
                    assert (wl.begin_state == prior_write_lock.end_state), "%s locks %s in state %s but previous %s leaves it in state %s" % (self, wl.locked_item, wl.begin_state, prior_write_lock.job, prior_write_lock.end_state)
                    self.depend_on.add(prior_write_lock.job)
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
                    self.wait_for.add(i.job)
            elif isinstance(lock, StateReadLock):
                rl = lock
                try:
                    prior_write_lock = StateWriteLock.filter_by_locked_item(rl.locked_item).filter(~Q(job__state = 'complete')).filter(job__id__lt = self.id).latest('id')
                    assert(prior_write_lock.end_state == rl.locked_state)
                    self.depend_on.add(prior_write_lock.job)
                except StateWriteLock.DoesNotExist:
                    pass

        self.wait_for_count = self.wait_for.count()
        self.depend_on_count = self.depend_on.count()
        self.save()

    def create_locks(self):
        from configure.lib.job import StateChangeJob
        # Take read lock on everything from self.get_deps
        for d in self.get_deps():
            depended_on, depended_state = d
            StateReadLock.objects.create(job = self, locked_item = depended_on, locked_state = depended_state)

        if isinstance(self, StateChangeJob):
            stateful_object = self.get_stateful_object()
            target_klass, old_state, new_state = self.state_transition

            # Take read lock on everything from get_stateful_object's get_deps if 
            # this is a StateChangeJob.  We do things depended on by both the old
            # and the new state: e.g. if we are taking a mount from unmounted->mounted
            # then we need to lock the new state's requirement of lnet_up, whereas
            # if we're going from mounted->unmounted we need to lock the old state's 
            # requirement of lnet_up (to prevent someone stopping lnet while 
            # we're still running)
            from itertools import chain
            for d in chain(stateful_object.get_deps(old_state), stateful_object.get_deps(new_state)):
                depended_on, depended_state, fix_state = d
                StateReadLock.objects.create(job = self,
                        locked_item = depended_on,
                        locked_state = depended_state)

            # Take a write lock on get_stateful_object if this is a StateChangeJob
            StateWriteLock.objects.create(
                    job = self,
                    locked_item = self.get_stateful_object(),
                    begin_state = old_state,
                    end_state = new_state)

    @classmethod
    def run_next(cls):
        from configure.lib.job import job_log
        from django.db.models import F
        runnable_jobs = Job.objects \
            .filter(wait_for_completions = F('wait_for_count')) \
            .filter(depend_on_completions = F('depend_on_count')) \
            .filter(state = 'pending')

        job_log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (runnable_jobs.count(), Job.objects.filter(state = 'pending').count(), Job.objects.filter(state = 'tasked').count()))
        for job in runnable_jobs:
            job.run()

    def get_deps(self):
        return []

    def get_steps(self):
        raise NotImplementedError()

    def cancel(self):
        from configure.lib.job import job_log
        job_log.debug("Job %d: Job.cancel" % self.id)
        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.
        from django.db import transaction
        @transaction.commit_on_success()
        def mark_cancelling():
            return Job.objects.filter(~Q(state = 'complete'), pk = self.id).update(state = 'cancelling')

        updated = mark_cancelling()
        if updated == 0:
            # Someone else already started this job, bug out
            job_log.debug("job %d already completed, not cancelling" % self.id)
            return

        if self.task_id:
            job_log.debug("job %d: revoking task %s" % (self.id, self.task_id))
            from celery.result import AsyncResult
            from celery.task.control import revoke
            revoke(self.task_id, terminate = True)
            self.task_id = None

        self.complete(cancelled = True)

    def pause(self):
        from configure.lib.job import job_log
        job_log.debug("Job %d: Job.pause" % self.id)
        print "Hey! pause!"
        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.
        from django.db import transaction
        @transaction.commit_on_success()
        def mark_paused():
            return Job.objects.filter(state = 'pending', pk = self.id).update(state = 'paused')

        updated = mark_paused()
        if updated != 1:
            job_log.warning("Job %d: failed to pause, it had already left state 'pending'")

    def unpause(self):
        from configure.lib.job import job_log
        job_log.debug("Job %d: Job.unpause" % self.id)
        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.
        from django.db import transaction
        @transaction.commit_on_success()
        def mark_unpaused():
            return Job.objects.filter(state = 'paused', pk = self.id).update(state = 'pending')

        updated = mark_unpaused()
        if updated != 1:
            job_log.warning("Job %d: failed to pause, it had already left state 'pending'" % self.id)
        else:
            job_log.warning("Job %d: unpaused, running any available jobs" % self.id)
            Job.run_next()


    def run(self):
        from configure.lib.job import job_log
        job_log.info("Job %d: Job.run" % self.id)
        # Important: multiple connections are allowed to call run() on a job
        # that they see as pending, but only one is allowed to proceed past this
        # point and spawn tasks.


        # My wait_for are complete, and I don't care if they're errored, just
        # that they aren't running any more.
        # My depend_on, however, must have completed successfully in order
        # to guarantee that my state dependencies have been met, so I will
        # error out if any depend_on are errored.
        for dep in self.depend_on.all():
            # My deps might have completed at some point in the past, or they
            # might be in the process of finishing and invoking their dependents
            # (of which I am one)
            assert(dep.state == 'complete' or dep.state == 'completing')
            if dep.errored or dep.cancelled:
                self.complete(cancelled = True)
                job_log.warning("Job %d: cancelling because depend_on %d was not successful" % (self.id, dep.id))
                return

        # Set state to 'tasked'
        # =====================
        from django.db import transaction
        @transaction.commit_on_success()
        def mark_tasked():
            return Job.objects.filter(pk = self.id, state = 'pending').update(state = 'tasking')

        updated = mark_tasked()

        if updated == 0:
            # Someone else already started this job, bug out
            job_log.debug("job %d already started running, backing off" % self.id)
            return
        else:
            assert(updated == 1)
            job_log.debug("job %d pending->tasking" % self.id)
            self.state = 'tasking'

        # Generate a celery task
        # ======================
        from configure.tasks import run_job
        celery_job = run_job.delay(self.id)

        # Save the celery task ID
        # =======================
        self.task_id = celery_job.task_id
        self.state = 'tasked'
        self.save()
        job_log.debug("job %d tasking->tasked (%s)" % (self.id, self.task_id))

    @classmethod
    def cancel_job(cls, job_id):
        job = Job.objects.get(pk = job_id)
        if job.state != 'tasked':
            return None

    def complete(self, errored = False, cancelled = False):
        from configure.lib.job import job_log
        success = not (errored or cancelled)
        if success and isinstance(self, StateChangeJob):
            new_state = self.state_transition[2]
            obj = self.get_stateful_object()
            obj.state = new_state
            job_log.info("StateChangeJob complete, setting state %s on %s" % (new_state, obj))
            obj.save()

        self.state = 'completing'
        self.errored = errored
        self.cancelled = cancelled
        self.save()

        job_log.info("job %d completing (errored=%s), notifying dependents" % (self.id, self.errored))
        for dependent in self.depend_on_job.all():
            dependent.notify_depend_on_complete()
        for dependent in self.wait_for_job.all():
            dependent.notify_wait_for_complete()

        Job.run_next()

        self.state = 'complete'
        self.errored = errored
        self.cancelled = cancelled
        self.save()

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


from configure.lib.job import StateChangeJob

class DependencyAbsent(Exception):
    """A Job wants to depend on something that doesn't exist"""
    pass

class ConfigureTargetMountJob(Job, StateChangeJob):
    state_transition = (ManagedTargetMount, 'unconfigured', 'configured')
    stateful_object = 'target_mount'
    state_verb = "Configure"
    target_mount = models.ForeignKey('ManagedTargetMount')

    def description(self):
        return "Configuring mount %s and HA for %s on %s" % (self.target_mount.mount_point, self.target_mount.target.name, self.target_mount.host)

    def get_steps(self):
        from configure.lib.job import ConfigurePacemakerStep
        return[(ConfigurePacemakerStep,
                      {'target_mount_id': self.target_mount.id})]

    def get_deps(self):
        deps = []

        # TODO: depend on unmounted OR mounted, to support adding a targetmount
        # to a target which is already up and running
        deps.append((self.target_mount.target.downcast(), "unmounted"))

        return deps

class RegisterTargetJob(Job, StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = (ManagedTarget, 'formatted', 'unmounted')
    stateful_object = 'target'
    state_verb = "Register"
    target = models.ForeignKey('ManagedTarget')

    def description(self):
        target = self.target.downcast()
        if isinstance(target, ManagedMgs):
            return "Register MGS"
        elif isinstance(target, ManagedOst):
            return "Register OST to filesystem %s" % target.filesystem.name
        elif isinstance(target, ManagedMdt):
            return "Register MDT to filesystem %s" % target.filesystem.name
        else:
            raise NotImplementedError()

    def get_steps(self):
        steps = []
        # FIXME: somehow need to avoid advertising this transition for MGS targets
        # currently as hack this is just a no-op for MGSs which marks them registered
        from configure.lib.job import RegisterTargetStep, NullStep
        target = self.target.downcast()
        if isinstance(target, ManagedMgs):
            steps.append((NullStep, {}))
        if isinstance(target, monitor_models.FilesystemMember):
            steps.append((RegisterTargetStep, {"target_mount_id": target.targetmount_set.get(primary = True).id}))

        return steps

    def get_deps(self):
        deps = []

        deps.append((self.target.targetmount_set.get(primary = True).host.downcast(), 'lnet_up'))

        # HYD-209
        # Registering an OST depends on the MDT having already been registered,
        # because in Lustre >= 2.0 MDT registration wipes previous OST registrations
        # such that for first mount you must already do mgs->mdt->osts
        #if isinstance(self.target, ManagedOst):
        #    try:
        #        mdt = ManagedMdt.objects.get(filesystem = self.target.filesystem)
        #    except ManagedMdt.DoesNotExist:
        #        raise DependencyAbsent("Cannot register OSTs for filesystem %s until an MDT is created" % self.target.filesystem)
        #    # TODO: depend on mdt in unmounted or mounted (i.e. registered)
        #    deps.append((mdt, "registered"))

        if isinstance(self.target, monitor_models.FilesystemMember):
            mgs = self.target.filesystem.mgs.downcast()
            deps.append((mgs, "mounted"))

        return deps

class StartTargetJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'unmounted', 'mounted')
    state_verb = "Start"
    target = models.ForeignKey(ManagedTarget)

    def description(self):
        return "Starting target %s" % self.target.downcast()

    def get_steps(self):
        from configure.lib.job import MountStep
        return [(MountStep, {"target_id": self.target.id})]

class StopTargetMountJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'mounted', 'unmounted')
    state_verb = "Stop"
    target = models.ForeignKey(ManagedTarget)

    def description(self):
        return "Stopping target %s" % self.target.downcast()

    def get_steps(self):
        from configure.lib.job import UnmountStep
        return [(UnmountStep, {"target_id": self.target.id})]

class FormatTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    target = models.ForeignKey(ManagedTarget)
    stateful_object = 'target'
    state_verb = 'Format'

    def description(self):
        target = self.target.downcast()
        if isinstance(target, ManagedMgs):
            return "Formatting MGS on %s" % target.targetmount_set.get(primary = True).host
        elif isinstance(target, ManagedMdt):
            return "Formatting MDT for filesystem %s" % target.filesystem.name
        elif isinstance(target, ManagedOst):
            return "Formatting OST for filesystem %s" % target.filesystem.name
        else:
            raise NotImplementedError()

    def get_steps(self):
        from configure.lib.job import MkfsStep
        return [(MkfsStep, {'target_id': self.target.id})]

class LoadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Load LNet'

    def description(self):
        return "Loading LNet module on %s" % self.host

    def get_steps(self):
        from configure.lib.job import LoadLNetStep
        return [(LoadLNetStep, {'host_id': self.host.id})]

class UnloadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Unload LNet'

    def description(self):
        return "Unloading LNet module on %s" % self.host

    def get_steps(self):
        from configure.lib.job import UnloadLNetStep
        return [(UnloadLNetStep, {'host_id': self.host.id})]
    
class StartLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Start LNet'

    def description(self):
        return "Start LNet on %s" % self.host

    def get_steps(self):
        from configure.lib.job import StartLNetStep
        return [(StartLNetStep, {'host_id': self.host.id})]

class StopLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Stop LNet'

    def description(self):
        return "Stop LNet on %s" % self.host

    def get_steps(self):
        from configure.lib.job import StopLNetStep
        return [(StopLNetStep, {'host_id': self.host.id})]

class ApplyConfParams(Job):
    mgs = models.ForeignKey(ManagedMgs)

    def description(self):
        return "Update conf_params on %s" % (self.mgs.primary_server())

    def get_steps(self):
        from configure.models import ConfParam
        from configure.lib.job import job_log
        new_params = ConfParam.objects.filter(version__gt = self.mgs.conf_param_version_applied).order_by('version')
        steps = []
        
        new_param_count = new_params.count()
        if new_param_count > 0:
            job_log.info("ApplyConfParams %d, applying %d new conf_params" % (self.id, new_param_count))
            # If we have some new params, create N ConfParamSteps and one ConfParamVersionStep
            from configure.lib.job import ConfParamStep, ConfParamVersionStep
            highest_version = 0
            for param in new_params:
                steps.append((ConfParamStep, {"conf_param_id": param.id}))
                highest_version = max(highest_version, param.version)
            steps.append((ConfParamVersionStep, {"mgs_id": self.mgs.id, "version": highest_version}))
        else:
            # If we have no new params, no-op
            job_log.warning("ApplyConfParams %d, mgs %d has no params newer than %d" % (self.id, self.mgs.id, self.mgs.conf_param_version_applied))
            from configure.lib.job import NullStep
            steps.append((NullStep, {}))

        return steps

    def get_deps(self):
        return [(self.mgs.targetmount_set.get(primary = True).downcast(), 'mounted')]

class ConfParam(models.Model):
    __metaclass__ = DowncastMetaclass
    mgs = models.ForeignKey(ManagedMgs)
    key = models.CharField(max_length = 512)
    # A None value means "lctl conf_param -d", i.e. clear the setting
    value = models.CharField(max_length = 512, blank = True, null = True)
    version = models.IntegerField()

    @staticmethod
    def get_latest_params(queryset):
        # Assumption: conf params don't experience high flux, so it's not 
        # obscenely inefficient to pull all historical values out of the DB before picking
        # the latest ones.
        from collections_24 import defaultdict
        by_key = defaultdict(list)
        for conf_param in queryset:
            by_key[conf_param.get_key()].append(conf_param)

        result_list = []
        for key, conf_param_list in by_key.items():
            conf_param_list.sort(lambda a,b: cmp(b.version, a.version))
            result_list.append(conf_param_list[0])

        return result_list

    def get_key(self):
        """Subclasses to return the fully qualified key, e.g. a FilesystemConfParam
           prepends the filesystem name to self.key"""
        return self.key

class FilesystemClientConfParam(ConfParam):
    filesystem = models.ForeignKey(ManagedFilesystem)
    def __init__(self, *args, **kwargs):
        super(FilesystemClientConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.filesystem.name, self.key)

class FilesystemGlobalConfParam(ConfParam):
    filesystem = models.ForeignKey(ManagedFilesystem)
    def __init__(self, *args, **kwargs):
        super(FilesystemGlobalConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.filesystem.name, self.key)

class MdtConfParam(ConfParam):
    # TODO: allow setting MDT to None to allow setting the param for 
    # all MDT on an MGS (and set this param for MDT in RegisterTargetJob)
    mdt = models.ForeignKey(ManagedMdt)
    def __init__(self, *args, **kwargs):
        super(MdtConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.mdt.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.mdt.name, self.key)

class OstConfParam(ConfParam):
    # TODO: allow setting OST to None to allow setting the param for 
    # all OSTs on an MGS (and set this param for OSTs in RegisterTargetJob)
    ost = models.ForeignKey(ManagedOst)
    def __init__(self, *args, **kwargs):
        super(OstConfParam, self).__init__(*args, **kwargs)
        self.mgs = self.ost.filesystem.mgs.downcast()

    def get_key(self):
        return "%s.%s" % (self.ost.name, self.key)

class VendorResourceRecord(models.Model):
    vendor_plugin = models.CharField(max_length = 256)
    vendor_class_str = models.TextField()
    vendor_id_str = models.TextField()
    vendor_id_scope = models.ForeignKey('VendorResourceRecord', blank = True, null = True)
    parents = models.ManyToManyField('VendorResourceRecord', related_name = 'resource_parent')
    vendor_dict_str = models.TextField()

