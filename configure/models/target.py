
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json
from re import escape

from django.db import models
from configure.lib.job import StateChangeJob, DependOn, DependAny, DependAll, Step, NullStep, AnyTargetMountStep, job_log
from configure.models.jobs import StatefulObject, Job
from monitor.models import DeletableDowncastableMetaclass, MeasuredEntity


class FilesystemMember(models.Model):
    """A Mountable for a particular filesystem, such as
       MDT, OST or Client"""
    filesystem = models.ForeignKey('ManagedFilesystem')

    # Use of abstract base classes to avoid django bug #12002
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
        return [(p.key, p.value) for p in self.targetparam_set.all()]

    def primary_host(self):
        from configure.models.target_mount import ManagedTargetMount
        return ManagedTargetMount.objects.get(target = self, primary = True).host

    def human_name(self):
        if self.name:
            return self.name
        else:
            return "Unregistered %s %s" % (self.downcast().role(), self.id)

    def __str__(self):
        return self.human_name()

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

        # FIXME: these alert updates should be in the same trans as
        # saving active_mount, otherwise next call we'll think active_mount is
        # already set, return out, and fail to update alerts

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

        if isinstance(self, FilesystemMember) and state != 'removed':
            # Make sure I'm removed if filesystem goes to 'removed'
            deps.append(DependOn(self.filesystem, 'available',
                acceptable_states = self.filesystem.not_state('removed'), fix_state='removed'))

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

    def get_lun(self):
        # FIXME: next time I'm breaking the schema, should make
        # lun an attribute of the ManagedTarget so that it
        # can be a OneToOne relation and thereby have a
        # contraint to ensure that two targets can't possibly use
        # the same Lun (and make this function redundant)
        return self.managedtargetmount_set.get(primary = True).block_device.lun

    def to_dict(self):
        active_host_name = "---"
        if self.active_mount:
            active_host_name = self.active_mount.host.pretty_name()

        from configure.models import ManagedTargetMount
        try:
            failover_server_name = self.managedtargetmount_set.get(primary = False).host.pretty_name()
        except ManagedTargetMount.DoesNotExist:
            failover_server_name = "---"

        if isinstance(self, FilesystemMember):
            filesystem_id = self.filesystem.pk
            filesystem_name = self.filesystem.name
        else:
            filesystem_id = None
            filesystem_name = None

        from django.contrib.contenttypes.models import ContentType

        return {'id': self.pk,
                'content_type_id': ContentType.objects.get_for_model(self.__class__).pk,
                'kind': self.role(),
                'human_name': self.human_name(),
                'lun_name': self.get_lun().human_name(),
                'active_host_name': active_host_name,
                'status': self.status_string(),
                'state': self.state,
                'primary_server_name': self.primary_server().pretty_name(),
                'failover_server_name': failover_server_name,
                'filesystem_id': filesystem_id,
                'filesystem_name': filesystem_name
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
        return "MGT"

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


class DeleteTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        from configure.models import ManagedTarget
        ManagedTarget.delete(kwargs['target_id'])


class RemoveRegisteredTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unmounted', 'removed')
    stateful_object = 'target'
    state_verb = "Remove"
    target = models.ForeignKey(ManagedTarget)

    requires_confirmation = True

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Removing target %s from configuration" % (self.target.downcast())

    def get_steps(self):
        # TODO: actually do something with Lustre before deleting this from our DB
        return [(DeleteTargetStep, {'target_id': self.target.id})]


# FIXME: this is a pretty horrible way of generating job classes for
# a number of originating states to the same end state
for origin in ['unformatted', 'formatted']:
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
        'Meta': type('Meta', (object,), {'app_label': 'configure'}),
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
        from configure.models import ManagedTargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = ManagedTargetMount.objects.get(id = target_mount_id)

        result = self.invoke_agent(target_mount.host, "register-target --device %s --mountpoint %s" % (target_mount.block_device.path, target_mount.mount_point))
        label = result['label']
        target = target_mount.target
        job_log.debug("Registration complete, updating target %d with name=%s" % (target.id, label))
        target.name = label
        target.save()


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
        from configure.models import ManagedTarget, ManagedHost, ManagedTargetMount
        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id)

        result = self._run_agent_command(target, "start-target --label %s --serial %s" % (target.name, target.pk))
        try:
            started_on = ManagedHost.objects.get(fqdn = result['location'])
        except ManagedHost.DoesNotExist:
            job_log.error("Target %s (%s) found on host %s, which is not a ManagedHost" % (target, target_id, result['location']))
            raise
        try:
            target.set_active_mount(target.managedtargetmount_set.get(host = started_on))
        except ManagedTargetMount.DoesNotExist:
            job_log.error("Target %s (%s) found on host %s (%s), which has no ManagedTargetMount for this target" % (target, target_id, started_on, started_on.pk))
            raise


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
        return [(MountStep, {"target_id": self.target.id})]


class UnmountStep(AnyTargetMountStep):
    idempotent = True

    def run(self, kwargs):
        from configure.models import ManagedTarget
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
        return [(UnmountStep, {"target_id": self.target.id})]


class MkfsStep(Step):
    def _mkfs_args(self, target):
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst, FilesystemMember
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
        from configure.models import ManagedTarget
        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id).downcast()
        target_mount = target.managedtargetmount_set.get(primary = True)
        return "Format %s on %s" % (target, target_mount.host)

    def run(self, kwargs):
        from configure.models import ManagedTarget

        target_id = kwargs['target_id']
        target = ManagedTarget.objects.get(id = target_id).downcast()

        target_mount = target.managedtargetmount_set.get(primary = True)
        # This is a primary target mount so must have a LunNode
        assert(target_mount.block_device != None)

        args = self._mkfs_args(target)
        result = self.invoke_agent(target_mount.host, "format-target --args %s" % escape(json.dumps(args)))
        fs_uuid = result['uuid']
        target.uuid = fs_uuid
        target.save()


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
        return [(MkfsStep, {'target_id': self.target.id})]
