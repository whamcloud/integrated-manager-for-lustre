
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from configure.lib.job import StateChangeJob, DependOn, DependAny, DependAll
from configure.models.jobs import StatefulObject, Job
from configure.models.target_mount import ManagedTargetMount
from monitor.models import DeletableDowncastableMetaclass, MeasuredEntity

class FilesystemMember(models.Model):
    """A Mountable for a particular filesystem, such as 
       MDT, OST or Client"""
    filesystem = models.ForeignKey('ManagedFilesystem')
    # uSE OF ABSTRACT BASE CLASSES TO AVOID DJANGO BUG #12002
    class Meta:
        abstract = True

class ManagedTarget(StatefulObject):
    __metaclass__ = DeletableDowncastableMetaclass
    # Like testfs-OST0001
    # Nullable because when manager creates a Target it doesn't know the name
    # until it's formatted+started+audited
    name = models.CharField(max_length = 64, null = True, blank = True)
    # Nullable because it is not known until the target is formatted
    uuid = models.CharField(max_length = 64, null = True, blank = True)

    def name_no_fs(self):
        """Something like OST0001 rather than testfs1-OST0001"""
        if self.name:
            if self.name.find("-") != -1:
                return self.name.split("-")[1]
            else:
                return self.name
        else:
            return self.downcast().role()

    def primary_server(self):
        return self.managedtargetmount_set.get(primary = True).host

    def failover_servers(self):
        for tm in self.managedtargetmount_set.filter(primary = False):
            yield tm.host

    def status_string(self, mount_statuses = None):
        if mount_statuses == None:
            mount_statuses = dict([(m, m.status_string()) for m in self.managedtargetmount_set.all()])

        if "STARTED" in mount_statuses.values():
            return "STARTED"
        elif "RECOVERY" in mount_statuses.values():
            return "RECOVERY"
        elif "FAILOVER" in mount_statuses.values():
            return "FAILOVER"
        else:
            return "STOPPED"
        # TODO: give statuses that reflect primary/secondaryness for FAILOVER

    def get_param(self, key):
        params = self.targetparam_set.filter(key = key)
        return [p.value for p in params]

    def get_params(self):
        return [(p.key,p.value) for p in self.targetparam_set.all()]

    def primary_host(self):
        return TargetMount.objects.get(target = self, primary = True).host

    def __str__(self):
        if self.name:
            return self.name
        else:
            return "Unregistered %s %s" % (self.downcast().role(), self.id)
    # unformatted: I exist in theory in the database 
    # formatted: I've been mkfs'd
    # unmounted: I've registered with the MGS, I'm not mounted
    # mounted: I've registered with the MGS, I'm mounted
    # removed: this target no longer exists in real life
    # Additional states needed for 'deactivated'?
    states = ['unformatted', 'formatted', 'unmounted', 'mounted', 'removed', 'autodetected']
    initial_state = 'unformatted'
    active_mount = models.ForeignKey('ManagedTargetMount', blank = True, null = True)

    def set_active_mount(self, active_mount):
        if self.active_mount == active_mount:
            return

        self.active_mount = active_mount
        self.save()

        from monitor.models import TargetFailoverAlert, TargetOfflineAlert
        TargetOfflineAlert.notify(self, active_mount == None)    
        for tm in self.managedtargetmount_set.filter(primary = False):
            TargetFailoverAlert.notify(tm, active_mount == tm)    

    class Meta:
        app_label = 'configure'

    def get_deps(self, state = None):
        if not state:
            state = self.state
        
        deps = []
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

        if isinstance(self, FilesystemMember) and self.state != 'removed':
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
            'ManagedTargetMount': (lambda mtm: ManagedTarget.objects.filter(pk = mtm.target_id)),
            'ManagedHost': managed_host_to_managed_targets,
            'ManagedFilesystem': lambda mfs: [t.downcast() for t in mfs.get_filesystem_targets()]
            }

class ManagedOst(ManagedTarget, FilesystemMember, MeasuredEntity):
    class Meta:
        app_label = 'configure'

    def __str__(self):
        if not self.name:
            return "Unregistered %s-OST" % (self.filesystem.name)
        else:
            return self.name

    def role(self):
        return "OST"

    def get_conf_params(self):
        from configure.models.conf_param import ConfParam
        return ConfParam.get_latest_params(self.ostconfparam_set.all())

    def default_mount_path(self, host):
        from configure.models import ManagedTargetMount
        counter = 0
        while True:
            candidate = "/mnt/%s/ost%d" % (self.filesystem.name, counter)
            try:
                ManagedTargetMount.objects.get(host = host, mount_point = candidate)
                counter = counter + 1
            except ManagedTargetMount.DoesNotExist:
                return candidate

class ManagedMdt(ManagedTarget, FilesystemMember, MeasuredEntity):
    # TODO: constraint to allow only one MetadataTarget per MGS.  The reason
    # we don't just use a OneToOneField is to use FilesystemMember to represent
    # MDTs and OSTs together in a convenient way
    class Meta:
        app_label = 'configure'

    def __str__(self):
        if not self.name:
            return "Unregistered %s-MDT" % (self.filesystem.name)
        else:
            return self.name

    def role(self):
        return "MDT"

    def get_conf_params(self):
        from configure.models.conf_param import ConfParam
        return ConfParam.get_latest_params(self.mdtconfparam_set.all())

    def default_mount_path(self, host):
        return "/mnt/%s/mdt" % self.filesystem.name

class ManagedMgs(ManagedTarget, MeasuredEntity):
    conf_param_version = models.IntegerField(default = 0)
    conf_param_version_applied = models.IntegerField(default = 0)

    def role(self):
        return "MGS"

    @classmethod
    def get_by_host(cls, host):
        return cls.objects.get(managedtargetmount__host = host)

    class Meta:
        app_label = 'configure'

    def default_mount_path(self, host):
        return "/mnt/mgs"

    def nids(self):
        """Return a list of NID strings"""
        nids = []
        for target_mount in self.managedtargetmount_set.all():
            host = target_mount.host.downcast()
            nids.extend(host.lnetconfiguration.get_nids())

        return nids

    def mgsnode_spec(self):
        """Return a list of strings of --mgsnode arguments suitable for use with mkfs"""
        result = []

        nids = ",".join(self.nids())
        assert(nids != "")
        result.append("--mgsnode=%s" % nids)

        return result

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
        from configure.models.conf_param import ConfParam
        return ConfParam.get_latest_params(self.confparam_set.all())

class RemoveRegisteredTargetJob(Job,StateChangeJob):
    state_transition = (ManagedTarget, 'unmounted', 'removed')
    stateful_object = 'target'
    state_verb = "Remove"
    target = models.ForeignKey(ManagedTarget)

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
        'target': models.ForeignKey(ManagedTarget),
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
    target = models.ForeignKey(ManagedTarget)

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
        if isinstance(target, FilesystemMember):
            steps.append((RegisterTargetStep, {"target_mount_id": target.managedtargetmount_set.get(primary = True).id}))

        return steps

    def get_deps(self):
        deps = []

        deps.append(DependOn(self.target.downcast().managedtargetmount_set.get(primary = True).host.downcast(), 'lnet_up'))

        if isinstance(self.target, FilesystemMember):
            mgs = self.target.filesystem.mgs.downcast()
            deps.append(DependOn(mgs, "mounted"))

        return DependAll(deps)

class StartTargetJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'unmounted', 'mounted')
    state_verb = "Start"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Starting target %s" % self.target.downcast()

    def get_deps(self):
        config_deps = []
        lnet_deps = []
        for tm in self.target.downcast().managedtargetmount_set.all():
            config_deps.append(DependOn(tm.downcast(), 'configured', fix_state = 'unmounted'))
            lnet_deps.append(DependOn(tm.host.downcast(), 'lnet_up', fix_state = 'unmounted'))
        # Depend on all targetmounts being configured
        # Depend on at least one targetmount having lnet up
        return DependAll([DependAny(lnet_deps), DependAll(config_deps)])

    def get_steps(self):
        from configure.lib.job import MountStep
        return [(MountStep, {"target_id": self.target.id})]

class StopTargetJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'mounted', 'unmounted')
    state_verb = "Stop"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Stopping target %s" % self.target.downcast()

    def get_deps(self):
        # Stopping a target requires all its targetmounts
        # to be in a configured state.
        deps = []
        for tm in self.target.downcast().managedtargetmount_set.all():
            deps.append(DependOn(tm.downcast(), 'configured'))
        return DependAll(deps)

    def get_steps(self):
        from configure.lib.job import UnmountStep
        return [(UnmountStep, {"target_id": self.target.id})]

class FormatTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    target = models.ForeignKey(ManagedTarget)
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

    def get_deps(self):
        target = self.target.downcast()
        deps = []

        for tm in target.managedtargetmount_set.all():
            host = tm.host.downcast()
            deps.append(DependOn(host.lnetconfiguration, 'nids_known'))

        if isinstance(target, FilesystemMember):
            for tm in target.filesystem.mgs.managedtargetmount_set.all():
                host = tm.host.downcast()
                lnet_configuration = host.lnetconfiguration
                deps.append(DependOn(lnet_configuration, 'nids_known'))
        return DependAll(deps)

    def get_steps(self):
        from configure.lib.job import MkfsStep
        return [(MkfsStep, {'target_id': self.target.id})]

