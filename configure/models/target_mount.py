
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from monitor import models as monitor_models
from configure.lib.job import StateChangeJob, DependOn, DependAny, DependAll
from configure.models.jobs import StatefulObject, Job

class ManagedTargetMount(monitor_models.TargetMount, StatefulObject):
    # unconfigured: I only exist in theory in the database
    # mounted: I am in fstab on the host and mounted
    # unmounted: I am in fstab on the host and unmounted
    states = ['unconfigured', 'configured', 'removed']
    initial_state = 'unconfigured'

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
            deps.append(DependOn(self.target_mount.target.targetmount_set.get(primary=True).downcast(), 'configured'))
        return DependAll(deps)


