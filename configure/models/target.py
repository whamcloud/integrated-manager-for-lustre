
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from monitor import models as monitor_models
from configure.lib.job import StateChangeJob, DependOn, DependAny, DependAll
from configure.models.jobs import StatefulObject, Job
from configure.models.target_mount import ManagedTargetMount

class ManagedTarget(StatefulObject):
    # unformatted: I exist in theory in the database 
    # formatted: I've been mkfs'd
    # unmounted: I've registered with the MGS, I'm not mounted
    # mounted: I've registered with the MGS, I'm mounted
    # removed: this target no longer exists in real life
    # Additional states needed for 'deactivated'?
    states = ['unformatted', 'formatted', 'unmounted', 'mounted', 'removed']
    initial_state = 'unformatted'
    active_mount = models.ForeignKey('ManagedTargetMount', blank = True, null = True)

    # ManagedTarget has to be abstract because ManagedOst et al are already
    # inheriting from Target.
    class Meta:
        app_label = 'configure'
        abstract = True


    def get_deps(self, state = None):
        if not state:
            state = self.state
        
        deps = []
        # TODO: ensure that active_mount is always set if 'mounted' by
        # having the agent return the active mount from the 'start' command.
        if state == 'mounted' and self.active_mount:
            # Depend on the TargetMount which is currently active being 
            # in state 'configured' and its host being in state 'lnet_up'
            # (in order to ensure that when lnet is stopped, this target will
            # be stopped, and if a TM is unconfigured then we will be 
            # unmounted while it happens)
            target_mount = self.active_mount
            deps.append(DependOn(target_mount.host.downcast(), 'lnet_up', fix_state='unmounted'))
            deps.append(DependOn(target_mount.downcast(), 'configured', fix_state='unmounted'))

            # TODO: also express that this situation may be resolved by migrating
            # the target instead of stopping it.

        if isinstance(self, monitor_models.FilesystemMember) and self.state != 'removed':
            # Make sure I'm removed if filesystem goes 'created'->'removed'
            deps.append(DependOn(self.filesystem.downcast(), 'created', fix_state='removed'))

        return DependAll(deps)

    def managed_host_to_managed_targets(mh):
        """Return iterable of all ManagedTargets which could potentially depend on the state
           of a managed host"""
        # Break this out into a function to avoid importing ManagedTargetMount at module scope
        from configure.models.target_mount import ManagedTargetMount
        return set([tm.target.downcast() for tm in ManagedTargetMount.objects.filter(host = mh)])

    reverse_deps = {
            'ManagedTargetMount': (lambda mtm: monitor_models.Target.objects.filter(pk = mtm.target_id)),
            'ManagedHost': managed_host_to_managed_targets,
            'ManagedFilesystem': lambda mfs: [t.downcast() for t in mfs.get_filesystem_targets()]
            }

class ManagedOst(monitor_models.ObjectStoreTarget, ManagedTarget):
    class Meta:
        app_label = 'configure'

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
    class Meta:
        app_label = 'configure'

    def get_conf_params(self):
        return ConfParam.get_latest_params(self.mdtconfparam_set.all())

    def default_mount_path(self, host):
        return "/mnt/%s/mdt" % self.filesystem.name

class ManagedMgs(monitor_models.ManagementTarget, ManagedTarget):
    conf_param_version = models.IntegerField(default = 0)
    conf_param_version_applied = models.IntegerField(default = 0)

    class Meta:
        app_label = 'configure'

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

class RemoveRegisteredTargetJob(Job,StateChangeJob):
    state_transition = (ManagedTarget, 'unmounted', 'removed')
    stateful_object = 'target'
    state_verb = "Remove"
    target = models.ForeignKey(monitor_models.Target)

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Removing target %s from configuration" % (self.target.downcast())

    def get_steps(self):
        # TODO: actually do something with Lustre before deleting this from our DB
        from configure.lib.job import DeleteTargetStep
        return [(DeleteTargetStep, {'target_id': self.target.id})]

# FIXME: this is a pretty horrible way of generating job classes for
# a number of originating states to the same end state
for origin in ['unformatted', 'formatted']:
    def description(self):
        return "Removing target %s from configuration" % (self.target.downcast())

    def get_steps(self):
        from configure.lib.job import DeleteTargetStep
        return [(DeleteTargetStep, {'target_id': self.target.id})]

    name = "RemoveTargetJob_%s" % origin
    cls = type(name, (Job, StateChangeJob), {
        'state_transition': (ManagedTarget, origin, 'removed'),
        'stateful_object': 'target',
        'state_verb': "Remove",
        'target': models.ForeignKey(monitor_models.Target),
        'Meta': type('Meta', (object,), {'app_label': 'configure'}),
        'description': description,
        'get_steps': get_steps,
        '__module__': __name__,
    })
    import sys
    this_module = sys.modules[__name__]
    setattr(this_module, name, cls)


class RegisterTargetJob(Job, StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = (ManagedTarget, 'formatted', 'unmounted')
    stateful_object = 'target'
    state_verb = "Register"
    target = models.ForeignKey(monitor_models.Target)

    class Meta:
        app_label = 'configure'

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

        deps.append(DependOn(self.target.downcast().targetmount_set.get(primary = True).host.downcast(), 'lnet_up'))

        if isinstance(self.target, monitor_models.FilesystemMember):
            mgs = self.target.filesystem.mgs.downcast()
            deps.append(DependOn(mgs, "mounted"))

        return DependAll(deps)

class StartTargetJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'unmounted', 'mounted')
    state_verb = "Start"
    target = models.ForeignKey(monitor_models.Target)

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Starting target %s" % self.target.downcast()

    def get_deps(self):
        # Depend on there being at least one targetmount which is in configured 
        # and whose host is in state lnet_up
        deps = []
        for tm in self.target.downcast().targetmount_set.all():
            deps.append(DependAll(
                DependOn(tm.downcast(), 'configured', fix_state = 'unmounted'),
                DependOn(tm.host.downcast(), 'lnet_up', fix_state = 'unmounted')
                ))
        return DependAny(deps)

    def get_steps(self):
        from configure.lib.job import MountStep
        return [(MountStep, {"target_id": self.target.id})]

class StopTargetJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'mounted', 'unmounted')
    state_verb = "Stop"
    target = models.ForeignKey(monitor_models.Target)

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Stopping target %s" % self.target.downcast()

    def get_steps(self):
        from configure.lib.job import UnmountStep
        return [(UnmountStep, {"target_id": self.target.id})]

class FormatTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    target = models.ForeignKey(monitor_models.Target)
    stateful_object = 'target'
    state_verb = 'Format'

    class Meta:
        app_label = 'configure'

    def description(self):
        target = self.target.downcast()
        if isinstance(target, ManagedMgs):
            return "Formatting MGS"
        elif isinstance(target, ManagedMdt):
            return "Formatting MDT for filesystem %s" % target.filesystem.name
        elif isinstance(target, ManagedOst):
            return "Formatting OST for filesystem %s" % target.filesystem.name
        else:
            raise NotImplementedError()

    def get_steps(self):
        from configure.lib.job import MkfsStep
        return [(MkfsStep, {'target_id': self.target.id})]



