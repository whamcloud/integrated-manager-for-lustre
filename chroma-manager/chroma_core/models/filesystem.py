#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db import models
from chroma_core.lib.job import  DependOn, DependAll, Step
from chroma_core.models.jobs import StatefulObject, StateChangeJob
from chroma_core.models.utils import DeletableDowncastableMetaclass, MeasuredEntity


class ManagedFilesystem(StatefulObject, MeasuredEntity):
    __metaclass__ = DeletableDowncastableMetaclass

    name = models.CharField(max_length=8, help_text="Lustre filesystem name, up to 8\
            characters")
    mgs = models.ForeignKey('ManagedMgs')

    states = ['unavailable', 'stopped', 'available', 'removed', 'forgotten']
    initial_state = 'unavailable'

    def get_label(self):
        return self.name

    def get_available_states(self, begin_state):
        available_states = super(ManagedFilesystem, self).get_available_states(begin_state)
        # Exclude 'stopped' if we are in 'unavailable' and everything is stopped
        target_states = set([t.state for t in self.get_filesystem_targets()])
        if begin_state == 'unavailable' and not 'mounted' in target_states:
            available_states = list(set(available_states) - set(['stopped']))

        return available_states

    class Meta:
        unique_together = ('name', 'mgs')

    def get_targets(self):
        return [self.mgs.downcast()] + self.get_filesystem_targets()

    def get_filesystem_targets(self):
        from chroma_core.models import ManagedOst, ManagedMdt
        osts = list(ManagedOst.objects.filter(filesystem = self).all())
        # NB using __str__ instead of name because name may not
        # be set in all cases
        osts.sort(lambda i, j: cmp(i.__str__()[-4:], j.__str__()[-4:]))

        return list(ManagedMdt.objects.filter(filesystem = self).all()) + osts

    def get_servers(self):
        from collections import defaultdict
        targets = self.get_targets()
        servers = defaultdict(list)
        for t in targets:
            for tm in t.managedtargetmount_set.all():
                servers[tm.host].append(tm)

        # NB converting to dict because django templates don't place nice with defaultdict
        # (http://stackoverflow.com/questions/4764110/django-template-cant-loop-defaultdict)
        return dict(servers)

    def mgs_spec(self):
        """Return a string which is foo in <foo>:/lustre for client mounts"""
        mgs = self.mgs
        nid_specs = []
        for target_mount in mgs.managedtargetmount_set.all():
            host = target_mount.host
            nids = ",".join(host.lnetconfiguration.get_nids())
            if nids == "":
                raise ValueError("NIDs for MGS host %s not known" % host)

            nid_specs.append(nids)

        return ":".join(nid_specs)

    def mount_command(self):
        try:
            return "mount -t lustre %s:/%s /mnt/%s" % (self.mgs_spec(), self.name, self.name)
        except ValueError:
            return None

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'chroma_core'

    def get_deps(self, state = None):
        if not state:
            state = self.state

        deps = []

        mgs = self.mgs.downcast()
        if state != 'removed':
            deps.append(DependOn(mgs,
                    'unmounted',
                    acceptable_states = mgs.not_state('removed'),
                    fix_state = 'removed'))

        if state == 'available':
            for t in self.get_targets():
                deps.append(DependOn(t,
                    'mounted',
                    fix_state = 'unavailable'))
        elif state == 'stopped':
            for t in self.get_filesystem_targets():
                deps.append(DependOn(t,
                    'unmounted',
                    acceptable_states = t.not_state('mounted'),
                    fix_state = 'unavailable'))

        return DependAll(deps)

    @classmethod
    def filter_by_target(self, target):
        from chroma_core.models import ManagedMgs
        target = target.downcast()
        if isinstance(target, ManagedMgs):
            return ManagedFilesystem.objects.filter(mgs = target)
        else:
            return [target.filesystem]


class DeleteFilesystemStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models.target import ManagedMdt, ManagedOst
        assert ManagedMdt.objects.filter(filesystem = kwargs['filesystem_id']).count() == 0
        assert ManagedOst.objects.filter(filesystem = kwargs['filesystem_id']).count() == 0
        ManagedFilesystem.delete(kwargs['filesystem_id'])


class RemoveFilesystemJob(StateChangeJob):
    state_transition = (ManagedFilesystem, 'stopped', 'removed')
    stateful_object = 'filesystem'
    state_verb = "Remove"
    filesystem = models.ForeignKey('ManagedFilesystem')

    def get_requires_confirmation(self):
        return True

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Removing filesystem %s from configuration" % (self.filesystem.name)

    def get_steps(self):
        return [(DeleteFilesystemStep, {'filesystem_id': self.filesystem.id})]


class FilesystemJob():
    stateful_object = 'filesystem'

    class Meta:
        app_label = 'chroma_core'

    def get_steps(self):
        from chroma_core.lib.job import NullStep
        return [(NullStep, {})]


class StartStoppedFilesystemJob(FilesystemJob, StateChangeJob):
    state_verb = "Start"
    state_transition = (ManagedFilesystem, 'stopped', 'available')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Start filesystem %s" % (self.filesystem.name)


class StartUnavailableFilesystemJob(FilesystemJob, StateChangeJob):
    state_verb = "Start"
    state_transition = (ManagedFilesystem, 'unavailable', 'available')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Start filesystem %s" % (self.filesystem.name)


class StopUnavailableFilesystemJob(FilesystemJob, StateChangeJob):
    state_verb = "Stop"
    state_transition = (ManagedFilesystem, 'unavailable', 'stopped')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Stop filesystem %s" % (self.filesystem.name)


class MakeAvailableFilesystemUnavailable(FilesystemJob, StateChangeJob):
    state_verb = None
    state_transition = (ManagedFilesystem, 'available', 'unavailable')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Make filesystem %s unavailable" % (self.filesystem.name)


class ForgetFilesystemJob(StateChangeJob):
    class Meta:
        app_label = 'chroma_core'

    state_transition = (ManagedFilesystem, ['unavailable', 'stopped', 'available'], 'forgotten')
    stateful_object = 'filesystem'
    state_verb = "Remove"
    filesystem = models.ForeignKey(ManagedFilesystem),
    requires_confirmation = True

    def description(self):
        return "Removing unmanaged filesystem %s" % (self.filesystem.name)

    def get_steps(self):
        return [(DeleteFilesystemStep, {'filesystem_id': self.filesystem.id})]
