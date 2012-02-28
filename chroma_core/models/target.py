
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json

from django.db import models, transaction
from chroma_core.lib.job import StateChangeJob, DependOn, DependAny, DependAll, Step, NullStep, AnyTargetMountStep, job_log
from chroma_core.models.jobs import StatefulObject, Job
from chroma_core.models.utils import DeletableDowncastableMetaclass, MeasuredEntity


class FilesystemMember(models.Model):
    """A Mountable for a particular filesystem, such as
       MDT, OST or Client"""
    filesystem = models.ForeignKey('ManagedFilesystem')

    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True


class ManagedTarget(StatefulObject):
    __metaclass__ = DeletableDowncastableMetaclass
    name = models.CharField(max_length = 64, null = True, blank = True,
            help_text = "Lustre target name, e.g. 'testfs-OST0001'.  May be null\
            if the target has not yet been registered.")
    uuid = models.CharField(max_length = 64, null = True, blank = True,
            help_text = "UUID of the target's internal filesystem.  May be null\
                    if the target has not yet been formatted")

    lun = models.ForeignKey('Lun')

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

    def secondary_servers(self):
        return [tm.host for tm in self.managedtargetmount_set.filter(primary = False)]

    def get_param(self, key):
        params = self.targetparam_set.filter(key = key)
        return [p.value for p in params]

    def get_params(self):
        return [(p.key, p.value) for p in self.targetparam_set.all()]

    def primary_host(self):
        from chroma_core.models.target_mount import ManagedTargetMount
        return ManagedTargetMount.objects.get(target = self, primary = True).host

    def get_label(self):
        if self.name:
            return self.name
        else:
            return "Unregistered %s %s" % (self.downcast().role(), self.id)

    def __str__(self):
        return self.get_label()

    # unformatted: I exist in theory in the database
    # formatted: I've been mkfs'd
    # registered: I've registered with the MGS, I'm not setup in HA yet
    # unmounted: I'm set up in HA, ready to mount
    # mounted: Im mounted
    # removed: this target no longer exists in real life
    # forgotten: Special "just delete it" state which bypasses transitions
    # Additional states needed for 'deactivated'?
    states = ['unformatted', 'formatted', 'registered', 'unmounted', 'mounted', 'removed', 'forgotten']
    initial_state = 'unformatted'
    active_mount = models.ForeignKey('ManagedTargetMount', blank = True, null = True)

    def set_active_mount(self, active_mount):
        if self.active_mount == active_mount:
            return

        from django.db import transaction
        with transaction.commit_on_success():
            # Doing an .update instead of .save() to avoid potentially
            # writing stale 'state' attribute (fixing HYD-619)
            ManagedTarget.objects.filter(pk = self.pk).update(active_mount = active_mount)

            from chroma_core.models import TargetFailoverAlert, TargetOfflineAlert
            TargetOfflineAlert.notify(self, active_mount == None)
            for tm in self.managedtargetmount_set.filter(primary = False):
                TargetFailoverAlert.notify(tm, active_mount == tm)

    class Meta:
        app_label = 'chroma_core'

    def get_deps(self, state = None):
        if not state:
            state = self.state

        deps = []
        if state == 'mounted' and self.active_mount and not self.immutable_state:
            # Depend on the active mount's host having LNet up, so that if
            # LNet is stopped on that host this target will be stopped first.
            target_mount = self.active_mount
            deps.append(DependOn(target_mount.host.downcast(), 'lnet_up', fix_state='unmounted'))

            # TODO: also express that this situation may be resolved by migrating
            # the target instead of stopping it.

        if isinstance(self, FilesystemMember) and state not in ['removed', 'forgotten']:
            # Make sure I follow if filesystem goes to 'removed'
            # or 'forgotten'
            if self.immutable_state:
                deps.append(DependOn(self.filesystem, 'available',
                    acceptable_states = self.filesystem.not_state('forgotten'), fix_state='forgotten'))
            else:
                deps.append(DependOn(self.filesystem, 'available',
                    acceptable_states = self.filesystem.not_state('removed'), fix_state='removed'))

        if state not in ['removed', 'forgotten']:
            for tm in self.managedtargetmount_set.all():
                if self.immutable_state:
                    deps.append(DependOn(tm.host.downcast(), 'lnet_up', acceptable_states = list(set(tm.host.states) - set(['removed', 'forgotten'])), fix_state = 'forgotten'))
                else:
                    deps.append(DependOn(tm.host.downcast(), 'lnet_up', acceptable_states = list(set(tm.host.states) - set(['removed', 'forgotten'])), fix_state = 'removed'))

        return DependAll(deps)

    def managed_host_to_managed_targets(mh):
        """Return iterable of all ManagedTargets which could potentially depend on the state
           of a managed host"""
        # Break this out into a function to avoid importing ManagedTargetMount at module scope
        from chroma_core.models.target_mount import ManagedTargetMount
        return set([tm.target.downcast() for tm in ManagedTargetMount.objects.filter(host = mh)])

    reverse_deps = {
            'ManagedTargetMount': (lambda mtm: ManagedTarget.objects.filter(pk = mtm.target_id)),
            'ManagedHost': managed_host_to_managed_targets,
            'ManagedFilesystem': lambda mfs: [t.downcast() for t in mfs.get_filesystem_targets()]
            }

    @classmethod
    def create_for_lun(cls, lun_id, **kwargs):
        # Local imports to avoid inter-model import dependencies
        from chroma_core.models.target_mount import ManagedTargetMount
        from chroma_core.models.host import Lun, LunNode

        lun = Lun.objects.get(pk = lun_id)

        target = cls(**kwargs)
        target.lun = lun
        target.save()

        def create_target_mount(lun_node):
            mount = ManagedTargetMount(
                block_device = lun_node,
                target = target,
                host = lun_node.host,
                mount_point = target.default_mount_path(lun_node.host),
                primary = lun_node.primary)
            mount.save()

        try:
            primary_lun_node = lun.lunnode_set.get(primary = True, host__not_deleted = True)
            create_target_mount(primary_lun_node)
        except LunNode.DoesNotExist:
            raise RuntimeError("No primary lun_node exists for lun %s, cannot created target" % lun)
        except LunNode.MultipleObjectsReturned:
            raise RuntimeError("Multiple primary lun_nodes exist for lun %s, internal error")

        for secondary_lun_node in lun.lunnode_set.filter(use = True, primary = False, host__not_deleted = True):
            create_target_mount(secondary_lun_node)

        return target


class ManagedOst(ManagedTarget, FilesystemMember, MeasuredEntity):
    class Meta:
        app_label = 'chroma_core'

    def __str__(self):
        if not self.name:
            return "Unregistered %s-OST" % (self.filesystem.name)
        else:
            return self.name

    def role(self):
        return "OST"

    def default_mount_path(self, host):
        from chroma_core.models import ManagedTargetMount
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
        app_label = 'chroma_core'

    def __str__(self):
        if not self.name:
            return "Unregistered %s-MDT" % (self.filesystem.name)
        else:
            return self.name

    def role(self):
        return "MDT"

    def default_mount_path(self, host):
        return "/mnt/%s/mdt" % self.filesystem.name


class ManagedMgs(ManagedTarget, MeasuredEntity):
    conf_param_version = models.IntegerField(default = 0)
    conf_param_version_applied = models.IntegerField(default = 0)

    def role(self):
        return "MGT"

    @classmethod
    def get_by_host(cls, host):
        return cls.objects.get(managedtargetmount__host = host)

    class Meta:
        app_label = 'chroma_core'

    def default_mount_path(self, host):
        return "/mnt/mgs"

    def nids(self):
        """Return a list of NID strings"""
        nids = []
        # Note: order by -primary in order that the first argument passed to mkfs
        # in failover configurations is the primary mount -- Lustre will use the
        # first --mgsnode argument as the NID to connect to for target registration,
        # and if that is the secondary NID then bad things happen during first
        # filesystem start.
        # HYD-521: need to verify that the mgsnode behaviour here is as expected
        for target_mount in self.managedtargetmount_set.all().order_by('-primary'):
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


class TargetRecoveryInfo(models.Model):
    """Record of what we learn from /proc/fs/lustre/*/*/recovery_status
       for a running target"""
    #: JSON-encoded dict parsed from /proc
    recovery_status = models.TextField()

    target = models.ForeignKey('chroma_core.ManagedTarget')

    class Meta:
        app_label = 'chroma_core'

    @staticmethod
    @transaction.commit_on_success
    def update(target, recovery_status):
        TargetRecoveryInfo.objects.filter(target = target).delete()
        instance = TargetRecoveryInfo.objects.create(
                target = target,
                recovery_status = json.dumps(recovery_status))
        return instance.is_recovering(recovery_status)

    def is_recovering(self, data = None):
        if not data:
            data = json.loads(self.recovery_status)
        return ("status" in data and data["status"] == "RECOVERING")

    def recovery_status_str(self):
        data = json.loads(self.recovery_status)
        if 'status' in data and data["status"] == "RECOVERING":
            return "%s %ss remaining" % (data["status"], data["time_remaining"])
        elif 'status' in data:
            return data["status"]
        else:
            return "N/A"


class DeleteTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        ManagedTarget.delete(kwargs['target_id'])


class RemoveConfiguredTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unmounted', 'removed')
    stateful_object = 'target'
    state_verb = "Remove"
    target = models.ForeignKey(ManagedTarget)

    requires_confirmation = True

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Removing target %s from configuration" % (self.target.downcast())

    def get_deps(self):
        deps = []

        return DependAll(deps)

    def get_steps(self):
        # TODO: actually do something with Lustre before deleting this from our DB
        steps = []
        for target_mount in self.target.managedtargetmount_set.all().order_by('primary'):
            steps.append((UnconfigurePacemakerStep, {'target_mount_id': target_mount.id}))
        steps.append((DeleteTargetStep, {'target_id': self.target.id}))
        return steps


# FIXME: this is a pretty horrible way of generating job classes for
# a number of originating states to the same end state
# TODO: when transitioning from 'registered' to 'removed', do something to
# remove this target from the MGS
for origin in ['unformatted', 'formatted', 'registered']:
    def description(self):
        return "Removing target %s from configuration" % (self.target.downcast())

    def get_steps(self):
        return [(DeleteTargetStep, {'target_id': self.target.id})]

    name = "RemoveTargetJob_%s" % origin
    cls = type(name, (Job, StateChangeJob), {
        'state_transition': (ManagedTarget, origin, 'removed'),
        'stateful_object': 'target',
        'state_verb': "Remove",
        'target': models.ForeignKey(ManagedTarget),
        'Meta': type('Meta', (object,), {'app_label': 'chroma_core'}),
        'description': description,
        'requires_confirmation': True,
        'get_steps': get_steps,
        '__module__': __name__,
    })
    import sys
    this_module = sys.modules[__name__]
    setattr(this_module, name, cls)


class RegisterTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedTargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = ManagedTargetMount.objects.get(id = target_mount_id)

        result = self.invoke_agent(target_mount.host, "register-target --device %s --mountpoint %s" % (target_mount.block_device.path, target_mount.mount_point))
        label = result['label']
        target = target_mount.target
        job_log.debug("Registration complete, updating target %d with name=%s" % (target.id, label))
        target.name = label
        target.save()


class ConfigurePacemakerStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedTargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = ManagedTargetMount.objects.get(id = target_mount_id)

        # target.name should have been populated by RegisterTarget
        assert(target_mount.block_device != None and target_mount.target.name != None)

        self.invoke_agent(target_mount.host, "configure-ha --device %s --label %s --uuid %s --serial %s %s --mountpoint %s" % (
                                    target_mount.block_device.path,
                                    target_mount.target.name,
                                    target_mount.target.uuid,
                                    target_mount.target.pk,
                                    target_mount.primary and "--primary" or "",
                                    target_mount.mount_point))


class UnconfigurePacemakerStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedTargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = ManagedTargetMount.objects.get(id = target_mount_id)

        # we would never have succeeded configuring in the first place if target
        # didn't have its name
        assert(target_mount.target.name != None)

        self.invoke_agent(target_mount.host, "unconfigure-ha --label %s --uuid %s --serial %s %s" % (
                                    target_mount.target.name,
                                    target_mount.target.uuid,
                                    target_mount.target.pk,
                                    target_mount.primary and "--primary" or ""))


class ConfigureTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'registered', 'unmounted')
    stateful_object = 'target'
    state_verb = "Configure mount points"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        target = self.target.downcast()
        return "Configuring %s mount points" % target

    def get_steps(self):
        steps = []

        for target_mount in self.target.managedtargetmount_set.all().order_by('-primary'):
            steps.append((ConfigurePacemakerStep, {'target_mount_id': target_mount.id}))

        return steps

    def get_deps(self):
        deps = []

        deps.append(DependOn(self.target.downcast().managedtargetmount_set.get(primary = True).host.downcast(), 'lnet_up'))

        if isinstance(self.target, FilesystemMember):
            mgs = self.target.filesystem.mgs.downcast()
            deps.append(DependOn(mgs, "mounted"))

        return DependAll(deps)


class RegisterTargetJob(Job, StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = (ManagedTarget, 'formatted', 'registered')
    stateful_object = 'target'
    state_verb = "Register"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'chroma_core'

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


class MountStep(AnyTargetMountStep):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedTarget, ManagedHost, ManagedTargetMount
        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id)

        result = self._run_agent_command(target, "start-target --label %s --serial %s" % (target.name, target.pk))
        try:
            started_on = ManagedHost.objects.get(nodename = result['location'])
        except ManagedHost.DoesNotExist:
            job_log.error("Target %s (%s) found on host %s, which is not a ManagedHost" % (target, target_id, result['location']))
            raise
        try:
            target.set_active_mount(target.managedtargetmount_set.get(host = started_on))
        except ManagedTargetMount.DoesNotExist:
            job_log.error("Target %s (%s) found on host %s (%s), which has no ManagedTargetMount for this target" % (target, target_id, started_on, started_on.pk))
            raise RuntimeError("Target %s reported as running on %s, but it is not configured there" % (target, started_on))


class StartTargetJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'unmounted', 'mounted')
    state_verb = "Start"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Starting target %s" % self.target.downcast()

    def get_deps(self):
        lnet_deps = []
        # Depend on at least one targetmount having lnet up
        for tm in self.target.downcast().managedtargetmount_set.all():
            lnet_deps.append(DependOn(tm.host.downcast(), 'lnet_up', fix_state = 'unmounted'))
        return DependAny(lnet_deps)

    def get_steps(self):
        return [(MountStep, {"target_id": self.target.id})]


class UnmountStep(AnyTargetMountStep):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedTarget
        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id)

        self._run_agent_command(target, "stop-target --label %s --serial %s" % (target.name, target.pk))
        target.set_active_mount(None)


class StopTargetJob(Job, StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'mounted', 'unmounted')
    state_verb = "Stop"
    target = models.ForeignKey(ManagedTarget)

    requires_confirmation = True

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Stopping target %s" % self.target.downcast()

    def get_steps(self):
        return [(UnmountStep, {"target_id": self.target.id})]


class MkfsStep(Step):
    def _mkfs_args(self, target):
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, FilesystemMember
        kwargs = {}
        primary_mount = target.managedtargetmount_set.get(primary = True)

        kwargs['target_types'] = {
            ManagedMgs: "mgs",
            ManagedMdt: "mdt",
            ManagedOst: "ost"
            }[target.__class__]

        if isinstance(target, FilesystemMember):
            kwargs['fsname'] = target.filesystem.name
            kwargs['mgsnode'] = target.filesystem.mgs.nids()

        kwargs['reformat'] = True

        fail_nids = []
        for secondary_mount in target.managedtargetmount_set.filter(primary = False):
            host = secondary_mount.host
            failhost_nids = host.lnetconfiguration.get_nids()
            assert(len(failhost_nids) != 0)
            fail_nids.extend(failhost_nids)
        if len(fail_nids) > 0:
            kwargs['failnode'] = fail_nids

        kwargs['device'] = primary_mount.block_device.path

        return kwargs

    @classmethod
    def describe(cls, kwargs):
        from chroma_core.models import ManagedTarget
        target_id = kwargs['target_id']
        target = ManagedTarget._base_manager.get(id = target_id).downcast()
        target_mount = target.managedtargetmount_set.get(primary = True)
        return "Format %s on %s" % (target, target_mount.host)

    def run(self, kwargs):
        from chroma_core.models import ManagedTarget

        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id).downcast()

        target_mount = target.managedtargetmount_set.get(primary = True)
        # This is a primary target mount so must have a LunNode
        assert(target_mount.block_device != None)

        args = self._mkfs_args(target)
        result = self.invoke_agent(target_mount.host, "format-target", args)
        fs_uuid = result['uuid']
        target.uuid = fs_uuid
        target.save()


class FormatTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    target = models.ForeignKey(ManagedTarget)
    stateful_object = 'target'
    state_verb = 'Format'

    class Meta:
        app_label = 'chroma_core'

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
        return [(MkfsStep, {'target_id': self.target.id})]


# Generate boilerplate classes for various origin->forgotten jobs.
# This may go away as a result of work tracked in HYD-627.
for origin in ['unmounted', 'mounted']:
    def forget_description(self):
        return "Removing unmanaged target %s" % (self.target.downcast())

    def forget_get_steps(self):
        return [(DeleteTargetStep, {'target_id': self.target.id})]

    name = "ForgetTargetJob_%s" % origin
    cls = type(name, (Job, StateChangeJob), {
        'state_transition': (ManagedTarget, origin, 'forgotten'),
        'stateful_object': 'target',
        'state_verb': "Remove",
        'target': models.ForeignKey(ManagedTarget),
        'Meta': type('Meta', (object,), {'app_label': 'chroma_core'}),
        'description': forget_description,
        'requires_confirmation': True,
        'get_steps': forget_get_steps,
        '__module__': __name__,
    })
    import sys
    this_module = sys.modules[__name__]
    setattr(this_module, name, cls)
