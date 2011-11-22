
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from configure.lib.job import StateChangeJob, DependOn, DependAll
from configure.models.jobs import Job
from configure.models.host import DeletableStatefulObject


class ManagedTargetMount(DeletableStatefulObject):
    """Associate a particular Lustre target with a device node on a host"""
    # FIXME: both LunNode and TargetMount refer to the host
    host = models.ForeignKey('ManagedHost')
    mount_point = models.CharField(max_length = 512, null = True, blank = True)
    block_device = models.ForeignKey('LunNode')
    primary = models.BooleanField()
    target = models.ForeignKey('ManagedTarget')

    # unconfigured: I only exist in theory in the database
    # mounted: I am in fstab on the host and mounted
    # unmounted: I am in fstab on the host and unmounted
    states = ['unconfigured', 'configured', 'removed', 'autodetected']
    initial_state = 'unconfigured'

    def save(self, force_insert = False, force_update = False, using = None):
        # If primary is true, then target must be unique
        if self.primary:
            from django.db.models import Q
            other_primaries = ManagedTargetMount.objects.filter(~Q(id = self.id), target = self.target, primary = True)
            if other_primaries.count() > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple primary mounts for target %s" % self.target)

        # If this is an MGS, there may not be another MGS on
        # this host
        from configure.models.target import ManagedMgs
        if isinstance(self.target.downcast(), ManagedMgs):
            from django.db.models import Q
            other_mgs_mountables_local = ManagedTargetMount.objects.filter(~Q(id = self.id), target__in = ManagedMgs.objects.all(), host = self.host).count()
            if other_mgs_mountables_local > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple MGS mounts on host %s" % self.host.address)

        return super(ManagedTargetMount, self).save(force_insert, force_update, using)

    def device(self):
        return self.block_device.path

    def status_string(self):
        from monitor.models import TargetRecoveryAlert
        in_recovery = (TargetRecoveryAlert.filter_by_item(self.target).count() > 0)
        if self.target.active_mount == self:
            if in_recovery:
                return "RECOVERY"
            elif self.primary:
                return "STARTED"
            else:
                return "FAILOVER"
        else:
            if self.primary:
                return "OFFLINE"
            else:
                return "SPARE"

    def pretty_block_device(self):
        # Truncate to iSCSI iqn if possible
        parts = self.block_device.path.split("-iscsi-")
        if len(parts) == 2:
            return parts[1]

        # Strip /dev/mapper if possible
        parts = self.block_device.path.split("/dev/mapper/")
        if len(parts) == 2:
            return parts[1]

        # Strip /dev if possible
        parts = self.block_device.path.split("/dev/")
        if len(parts) == 2:
            return parts[1]

        # Fall through, do nothing
        return self.block_device

    class Meta:
        app_label = 'configure'

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
            # Depend on target in state unmounted OR mounted
            # in order to get this unconfigured when the target is removed.
            deps.append(DependOn(self.target.downcast(), 'unmounted', acceptable_states = ['mounted', 'unmounted'], fix_state = 'removed'))
        elif state == 'unconfigured':
            acceptable_target_states = set(self.target.downcast().states) - set(['removed'])
            deps.append(DependOn(self.target.downcast(), 'unmounted', acceptable_states = acceptable_target_states, fix_state = 'removed'))

        if state != 'removed':
            # In all states but removed, depend on the host not being removed
            acceptable_host_states = set(self.host.downcast().states) - set(['removed'])
            # FIXME: the 'preferred' state is actually irrelevant in calls like this
            # which only exist to get our fix_state set when the dependency leaves the set of
            # acceptable states, it's noise.
            deps.append(DependOn(self.host.downcast(), 'lnet_up', acceptable_states = acceptable_host_states, fix_state = 'removed'))

        return DependAll(deps)

    # Reverse dependencies are records of other classes which must check
    # our get_deps when they change state.
    # It tells them how, given an instance of the other class, to find
    # instances of this class which may depend on it.
    reverse_deps = {
            # We depend on it being in a registered state
            'ManagedTarget': (lambda mt: ManagedTargetMount.objects.filter(target = mt)),
            'ManagedHost': (lambda mh: ManagedTargetMount.objects.filter(host = mh)),
            }


class RemoveTargetMountJob(Job, StateChangeJob):
    state_transition = (ManagedTargetMount, 'configured', 'removed')
    stateful_object = 'target_mount'
    state_verb = "Remove"
    target_mount = models.ForeignKey('ManagedTargetMount')

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Removing target mount %s from configuration" % (self.target_mount.downcast())

    def get_steps(self):
        from configure.lib.job import UnconfigurePacemakerStep, DeleteTargetMountStep
        return [(UnconfigurePacemakerStep, {'target_mount_id': self.target_mount.id}),
                (DeleteTargetMountStep, {'target_mount_id': self.target_mount.id})]

    def get_deps(self):
        deps = []
        deps.append(DependOn(self.target_mount.target.downcast(), 'unmounted'))
        if self.target_mount.primary:
            for tm in self.target_mount.target.managedtargetmount_set.filter(primary = False):
                deps.append(DependOn(tm.downcast(), 'removed'))
        return DependAll(deps)


class RemoveUnconfiguredTargetMountJob(Job, StateChangeJob):
    state_transition = (ManagedTargetMount, 'unconfigured', 'removed')
    stateful_object = 'target_mount'
    state_verb = "Remove"
    target_mount = models.ForeignKey('ManagedTargetMount')

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Removing target mount %s from configuration" % (self.target_mount.downcast())

    def get_steps(self):
        from configure.lib.job import DeleteTargetMountStep
        return [(DeleteTargetMountStep, {'target_mount_id': self.target_mount.id})]


class ConfigureTargetMountJob(Job, StateChangeJob):
    state_transition = (ManagedTargetMount, 'unconfigured', 'configured')
    stateful_object = 'target_mount'
    state_verb = "Configure"
    target_mount = models.ForeignKey('ManagedTargetMount')

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Configuring %s on %s" % (self.target_mount.target.downcast(), self.target_mount.host)

    def get_steps(self):
        from configure.lib.job import ConfigurePacemakerStep
        return[(ConfigurePacemakerStep, {'target_mount_id': self.target_mount.id})]

    def get_deps(self):
        # To configure a TM for a target, required that it is in a
        # registered state
        deps = []
        deps.append(DependOn(self.target_mount.target.downcast(), preferred_state = 'unmounted', acceptable_states = ['unmounted', 'mounted']))
        if not self.target_mount.primary:
            deps.append(DependOn(self.target_mount.target.managedtargetmount_set.get(primary=True).downcast(), 'configured'))
        return DependAll(deps)
