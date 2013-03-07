#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db import models
from chroma_core.lib.job import DependOn, DependAll, Step, job_log
from chroma_core.models.target import ManagedTargetMount, ManagedMgs, FilesystemMember, ManagedTarget
from chroma_core.models.host import NoLNetInfo
from chroma_core.models.jobs import StatefulObject, StateChangeJob, StateLock
from chroma_core.models.utils import DeletableDowncastableMetaclass, MeasuredEntity
from chroma_core.lib.cache import ObjectCache
from django.db.models import Q


class ManagedFilesystem(StatefulObject, MeasuredEntity):
    __metaclass__ = DeletableDowncastableMetaclass

    name = models.CharField(max_length=8, help_text="Lustre filesystem name, up to 8\
            characters")
    mgs = models.ForeignKey('ManagedMgs')

    states = ['unavailable', 'stopped', 'available', 'removed', 'forgotten']
    initial_state = 'unavailable'

    mdt_next_index = models.IntegerField(default = 0)
    ost_next_index = models.IntegerField(default = 0)

    def get_label(self):
        return self.name

    def get_available_states(self, begin_state):
        if self.immutable_state:
            return ['forgotten']
        else:
            available_states = super(ManagedFilesystem, self).get_available_states(begin_state)
            available_states = list(set(available_states) - set(['forgotten']))

            # Exclude 'stopped' if we are in 'unavailable' and everything is stopped
            target_states = set([t.state for t in self.get_filesystem_targets()])
            if begin_state == 'unavailable' and not 'mounted' in target_states:
                available_states = list(set(available_states) - set(['stopped']))

            return available_states

    class Meta:
        app_label = 'chroma_core'
        unique_together = ('name', 'mgs')
        ordering = ['id']

    def get_targets(self):
        return ManagedTarget.objects.filter((Q(managedmdt__filesystem = self) | Q(managedost__filesystem = self)) | Q(id = self.mgs_id))

    def get_filesystem_targets(self):
        return ManagedTarget.objects.filter((Q(managedmdt__filesystem = self) | Q(managedost__filesystem = self)))

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
        return ":".join([",".join(nids) for nids in self.mgs.nids()])

    def mount_path(self):
        try:
            return "%s:/%s" % (self.mgs_spec(), self.name)
        except NoLNetInfo:
            return None

    def __str__(self):
        return self.name

    def get_deps(self, state = None):
        if not state:
            state = self.state

        deps = []

        mgs = ObjectCache.get_one(ManagedTarget, lambda t: t.id == self.mgs_id)

        remove_state = 'forgotten' if self.immutable_state else 'removed'

        if state not in ['removed', 'forgotten']:
            deps.append(DependOn(mgs,
                'unmounted',
                acceptable_states = mgs.not_states(['removed', 'forgotten']),
                fix_state = remove_state))

        return DependAll(deps)

    @classmethod
    def filter_by_target(cls, target):
        if issubclass(target.downcast_class, ManagedMgs):
            result = ObjectCache.get(ManagedFilesystem, lambda mfs: mfs.mgs_id == target.id)
            return result
        elif issubclass(target.downcast_class, FilesystemMember):
            return ObjectCache.get(ManagedFilesystem, lambda mfs: mfs.id == target.downcast().filesystem_id)
        else:
            raise NotImplementedError(target.__class__)

    reverse_deps = {
        'ManagedTarget': lambda mt: ManagedFilesystem.filter_by_target(mt)
    }


class PurgeFilesystemStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        mgs_device_path = kwargs['path']
        fs = kwargs['filesystem']
        mgs = ObjectCache.get_one(ManagedTarget, lambda t: t.id == fs.mgs_id)

        initial_mgs_state = mgs.state

        # Whether the MGS was officially up or not, try stopping it (idempotent so will
        # succeed either way
        if initial_mgs_state in ['mounted', 'unmounted']:
            self.invoke_agent(host, "stop_target", {'ha_label': mgs.ha_label})
        self.invoke_agent(host, "purge_configuration", {
            'device': mgs_device_path,
            'filesystem_name': fs.name
        })

        if initial_mgs_state == 'mounted':
            result = self.invoke_agent(host, "start_target", {'ha_label': mgs.ha_label})
            # Update active_mount because it won't necessarily start the same place it was started to
            # begin with
            mgs.update_active_mount(result['location'])


class RemoveFilesystemJob(StateChangeJob):
    state_transition = (ManagedFilesystem, 'stopped', 'removed')
    stateful_object = 'filesystem'
    state_verb = "Remove"
    filesystem = models.ForeignKey('ManagedFilesystem')

    def get_requires_confirmation(self):
        return True

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Remove file system %s from configuration" % self.filesystem.name

    def create_locks(self):
        locks = super(RemoveFilesystemJob, self).create_locks()
        locks.append(StateLock(
            job = self,
            locked_item = self.filesystem.mgs.managedtarget_ptr,
            begin_state = None,
            end_state = None,
            write = True))
        return locks

    def get_steps(self):
        steps = []

        # Only try to purge filesystem from MGT if the MGT has made it past
        # being formatted (case where a filesystem was created but is being
        # removed before it or its MGT got off the ground)
        mgt_setup = self.filesystem.mgs.state not in ['unformatted', 'formatted']

        if (not self.filesystem.immutable_state) and mgt_setup:
            mgs = ObjectCache.get_one(ManagedTarget, lambda t: t.id == self.filesystem.mgs_id)
            mgs_primary_mount = ObjectCache.get_one(ManagedTargetMount, lambda mtm: mtm.target_id == mgs.id and mtm.primary is True)

            steps.append((PurgeFilesystemStep, {
                'filesystem': self.filesystem,
                'path': mgs_primary_mount.volume_node.path,
                'host': mgs_primary_mount.host
            }))

        return steps

    def on_success(self):
        job_log.debug("on_success: mark_deleted on filesystem %s" % id(self.filesystem))

        from chroma_core.models.target import ManagedMdt, ManagedOst
        assert ManagedMdt.objects.filter(filesystem = self.filesystem).count() == 0
        assert ManagedOst.objects.filter(filesystem = self.filesystem).count() == 0
        self.filesystem.mark_deleted()

        super(RemoveFilesystemJob, self).on_success()


class FilesystemJob():
    stateful_object = 'filesystem'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_steps(self):
        return []


class StartStoppedFilesystemJob(FilesystemJob, StateChangeJob):
    state_verb = "Start"
    state_transition = (ManagedFilesystem, 'stopped', 'available')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Start file system %s" % self.filesystem.name

    def get_deps(self):
        deps = []

        for t in ObjectCache.get_targets_by_filesystem(self.filesystem_id):
            deps.append(DependOn(t,
                'mounted',
                fix_state = 'unavailable'))
        return DependAll(deps)


class StartUnavailableFilesystemJob(FilesystemJob, StateChangeJob):
    state_verb = "Start"
    state_transition = (ManagedFilesystem, 'unavailable', 'available')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Start filesystem %s" % self.filesystem.name

    def get_deps(self):
        deps = []
        for t in ObjectCache.get_targets_by_filesystem(self.filesystem_id):
            deps.append(DependOn(t,
                'mounted',
                fix_state = 'unavailable'))
        return DependAll(deps)


class StopUnavailableFilesystemJob(FilesystemJob, StateChangeJob):
    state_verb = "Stop"
    state_transition = (ManagedFilesystem, 'unavailable', 'stopped')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Stop file system %s" % self.filesystem.name

    def get_deps(self):
        deps = []
        targets = ObjectCache.get_targets_by_filesystem(self.filesystem_id)
        targets = [t for t in targets if not issubclass(t.downcast_class, ManagedMgs)]
        for t in targets:
            deps.append(DependOn(t,
                'unmounted',
                acceptable_states = t.not_state('mounted'),
                fix_state = 'unavailable'))
        return DependAll(deps)


class MakeAvailableFilesystemUnavailable(FilesystemJob, StateChangeJob):
    state_verb = None
    state_transition = (ManagedFilesystem, 'available', 'unavailable')
    filesystem = models.ForeignKey('ManagedFilesystem')

    def description(self):
        return "Make file system %s unavailable" % self.filesystem.name


class ForgetFilesystemJob(StateChangeJob):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    state_transition = (ManagedFilesystem, ['unavailable', 'stopped', 'available'], 'forgotten')
    stateful_object = 'filesystem'
    state_verb = "Remove"
    filesystem = models.ForeignKey(ManagedFilesystem)
    requires_confirmation = True

    def description(self):
        return "Remove unmanaged file system %s" % self.filesystem.name

    def on_success(self):
        super(ForgetFilesystemJob, self).on_success()

        from chroma_core.models.target import ManagedMdt, ManagedOst
        assert ManagedMdt.objects.filter(filesystem = self.filesystem).count() == 0
        assert ManagedOst.objects.filter(filesystem = self.filesystem).count() == 0
        self.filesystem.mark_deleted()
