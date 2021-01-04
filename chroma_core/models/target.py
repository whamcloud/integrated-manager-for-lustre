# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import json
import logging
from chroma_core.lib.cache import ObjectCache
from django.db import models, transaction
from django.db.models import CASCADE
from chroma_core.lib.job import DependOn, DependAny, DependAll, Step, job_log
from chroma_core.models.event import AlertEvent
from chroma_core.models.alert import AlertStateBase
from chroma_core.models.jobs import StateChangeJob, StateLock, AdvertisedJob
from chroma_core.models.host import ManagedHost, HostContactAlert
from chroma_core.models.jobs import StatefulObject
from chroma_core.models.pacemaker import PacemakerConfiguration
from chroma_core.models.utils import DeletableDowncastableMetaclass
from chroma_help.help import help_text
from iml_common.lib import util

import settings


class NotAFileSystemMember(Exception):
    pass


class FilesystemMember(models.Model):
    """A Mountable for a particular filesystem, such as
    MDT, OST or Client"""

    filesystem = models.ForeignKey("ManagedFilesystem", on_delete=CASCADE)
    index = models.IntegerField()

    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True


# select_description
#
# This little nugget selects from a dict of class: description to
# return the description that matches the that class or subclass in the
# key
#
# Probably called like this
#
# select_description(stateful_object,
#                    {ManagedOst: help_text["stop_ost"],
#                     ManagedMgs: help_text["stop_mgt"],
#                     ManagedMdt: help_text["stop_mdt"]})
def select_description(stateful_object, descriptions):
    def match(class_to_compare):
        return issubclass(stateful_object.downcast_class, class_to_compare)

    for class_to_compare, desc in descriptions.iteritems():
        if match(class_to_compare):
            return desc

    match_class_names = ", ".join(class_to_compare.__name__ for class_to_compare in descriptions.keys())

    raise RuntimeError("Could not find %s in %s" % (stateful_object.downcast_class.__name__, match_class_names))


class ManagedTarget(StatefulObject):
    __metaclass__ = DeletableDowncastableMetaclass
    name = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Lustre target name, e.g. 'testfs-OST0001'.  May be null\
                            if the target has not yet been registered.",
    )

    uuid = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="UUID of the target's internal file system.  May be null\
                            if the target has not yet been formatted",
    )

    ha_label = models.CharField(
        max_length=64, null=True, blank=True, help_text="Label used for HA layer; human readable but unique"
    )

    inode_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes per inode")
    bytes_per_inode = models.IntegerField(
        null=True,
        blank=True,
        help_text="Constant used during formatting to "
        "determine inode count by dividing the volume size by ``bytes_per_inode``",
    )
    inode_count = models.BigIntegerField(
        null=True, blank=True, help_text="The number of inodes in this target's" "backing store"
    )

    reformat = models.BooleanField(
        default=False,
        help_text="Only used during formatting, indicates that when formatting this target \
        any existing filesystem on the Volume should be overwritten",
    )

    def get_param(self, key):
        params = self.targetparam_set.filter(key=key)
        return [p.value for p in params]

    def get_params(self):
        return [(p.key, p.value) for p in self.targetparam_set.all()]

    @property
    def first_known_host(self):
        t = get_target_by_name(self.name)

        host_id = t.get("host_ids")[0]

        return ManagedHost.objects.get(id=host_id)

    @property
    def inactive_hosts(self):
        t = get_target_by_name(self.name)

        host_id = t.get("active_host_id")

        host_ids = t.get("host_ids")

        xs = [x for x in host_ids if x != host_id]

        return ManagedHost.objects.filter(id__in=xs, not_deleted=True)

    @property
    def hosts(self):
        t = get_target_by_name(self.name)

        host_ids = t.get("host_ids")

        return ManagedHost.objects.filter(id__in=host_ids, not_deleted=True)

    @property
    def default_mount_point(self):
        return "/mnt/%s" % self.name

    @property
    def active_host(self):
        t = get_target_by_name(self.name)

        id = t.get("active_host_id")

        if id is None:
            return None

        return ManagedHost.objects.get(id=id)

    def get_label(self):
        return self.name

    def __str__(self):
        return self.name or ""

    def best_available_host(self):
        """
        :return: A host which is available for actions, preferably the one running this target.
        """

        t = get_target_by_name(self.name)
        xs = [t.get("active_host_id")] if t.get("active_host_id") else []
        xs = xs + t["host_ids"]
        xs = filter(lambda x: HostContactAlert.filter_by_item_id(ManagedHost, x).count() == 0, xs)

        if len(xs) == 0:
            raise ManagedHost.DoesNotExist("No hosts online for {}".format(t["name"]))

        return ManagedHost.objects.get(id=xs[0])

    # unformatted: I exist in theory in the database
    # formatted: I've been mkfs'd
    # registered: I've registered with the MGS, I'm not setup in HA yet
    # unmounted: I'm set up in HA, ready to mount
    # mounted: Im mounted
    # removed: this target no longer exists in real life
    # forgotten: Equivalent of 'removed' for immutable_state targets
    # Additional states needed for 'deactivated'?
    states = ["unformatted", "formatted", "registered", "unmounted", "mounted", "removed", "forgotten"]
    initial_state = "unformatted"

    def set_state(self, state, intentional=False):
        job_log.debug("mt.set_state %s %s" % (state, intentional))
        super(ManagedTarget, self).set_state(state, intentional)
        if intentional:
            TargetOfflineAlert.notify_warning(self, self.state == "unmounted")
        else:
            TargetOfflineAlert.notify(self, self.state == "unmounted")

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_deps(self, state=None):
        if not state:
            state = self.state

        t = get_target_by_name(self.name)
        active_host_id = t["active_host_id"]

        deps = []
        if state == "mounted" and active_host_id and not self.immutable_state:
            from chroma_core.models import LNetConfiguration

            # Depend on the active mount's host having LNet up, so that if
            # LNet is stopped on that host this target will be stopped first.
            host = ObjectCache.get_one(ManagedHost, lambda mh: mh.id == active_host_id, fill_on_miss=True)

            lnet_configuration = ObjectCache.get_by_id(LNetConfiguration, host.lnet_configuration.id)
            deps.append(DependOn(lnet_configuration, "lnet_up", fix_state="unmounted"))

            if host.pacemaker_configuration:
                pacemaker_configuration = ObjectCache.get_by_id(PacemakerConfiguration, host.pacemaker_configuration.id)
                deps.append(DependOn(pacemaker_configuration, "started", fix_state="unmounted"))

            # TODO: also express that this situation may be resolved by migrating
            # the target instead of stopping it.

        if state not in ["removed", "forgotten"]:
            from chroma_core.models import LNetConfiguration

            for host in self.hosts:
                fix_state = "forgotten" if self.immutable_state else "removed"

                lnet_configuration = ObjectCache.get_by_id(LNetConfiguration, host.lnet_configuration.id)
                deps.append(
                    DependOn(lnet_configuration, "lnet_up", unacceptable_states=["unconfigured"], fix_state=fix_state)
                )

                if host.pacemaker_configuration:
                    pacemaker_configuration = ObjectCache.get_by_id(
                        PacemakerConfiguration, host.pacemaker_configuration.id
                    )
                    deps.append(
                        DependOn(
                            pacemaker_configuration,
                            "started",
                            unacceptable_states=["unconfigured"],
                            fix_state=fix_state,
                        )
                    )

        return DependAll(deps)

    reverse_deps = {
        "ManagedHost": lambda mh: get_host_targets(mh.id),
        "LNetConfiguration": lambda lc: get_host_targets(lc.host.id),
        "PacemakerConfiguration": lambda pc: get_host_targets(pc.host.id),
        "ManagedFilesystem": lambda mfs: ObjectCache.fs_targets(mfs.id),
    }

    def target_type(self):
        raise NotImplementedError("Unimplemented method 'target_type'")

    @classmethod
    def managed_target_of_type(cls, target_type):
        """
        :param target_type:  is a string describing the target required, generally ost, mdt or mgt
        :return: Returns a klass of the type required by looking through the subclasses
        """
        try:
            # Hack I need to work out with Joe.
            if target_type == "mgt":
                target_type = "mgs"

            target_type = target_type.lower()

            subtype = next(
                klass for klass in util.all_subclasses(ManagedTarget) if target_type == klass().target_type()
            )

            return subtype
        except StopIteration:
            raise NotImplementedError("ManagedTarget %s unknown" % target_type)

    @property
    def filesystem_member(self):
        """
        :return: True if the TargetType is a file system member, generally OST or MDT.
        """
        return issubclass(type(self), FilesystemMember)

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        """Allows a ManagedTarget to modify the mkfs_options as required.
        :return: A list of additional options for mkfs as in those things that appear after --mkfsoptions
        """
        return mkfs_options


class ManagedOst(ManagedTarget, FilesystemMember):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_available_states(self, begin_state):
        # Exclude the transition to 'removed' in favour of being removed when our FS is
        if self.immutable_state:
            return []
        else:
            available_states = super(ManagedOst, self).get_available_states(begin_state)
            available_states = list(set(available_states) - set(["forgotten"]))
            return available_states

    def target_type(self):
        return "ost"

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        if (settings.JOURNAL_SIZE is not None) and (filesystemtype == "ldiskfs"):
            mkfs_options.append("-J size=%s" % settings.JOURNAL_SIZE)

        # HYD-1089 should supercede these settings
        if settings.LUSTRE_MKFS_OPTIONS_OST:
            mkfs_options = [settings.LUSTRE_MKFS_OPTIONS_OST]

        return mkfs_options


class ManagedMdt(ManagedTarget, FilesystemMember):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_available_states(self, begin_state):
        # Exclude the transition to 'removed' in favour of being removed when our FS is
        if self.immutable_state:
            return []
        else:
            available_states = super(ManagedMdt, self).get_available_states(begin_state)
            available_states = list(set(available_states) - set(["removed", "forgotten"]))

            return available_states

    def target_type(self):
        return "mdt"

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        if (settings.JOURNAL_SIZE is not None) and (filesystemtype == "ldiskfs"):
            mkfs_options += ["-J size=%s" % settings.JOURNAL_SIZE]

        # HYD-1089 should supercede these settings
        if settings.LUSTRE_MKFS_OPTIONS_MDT:
            mkfs_options = [settings.LUSTRE_MKFS_OPTIONS_MDT]

        return mkfs_options


class ManagedMgs(ManagedTarget):
    conf_param_version = models.IntegerField(default=0)
    conf_param_version_applied = models.IntegerField(default=0)

    def get_available_states(self, begin_state):
        if self.immutable_state:
            if self.managedfilesystem_set.count() == 0:
                return ["forgotten"]
            else:
                return []
        else:
            available_states = super(ManagedMgs, self).get_available_states(begin_state)
            excluded_states = []

            # Exclude the transition to 'forgotten' if multiple filesystems
            if self.managedfilesystem_set.count():
                excluded_states.append("forgotten")

            # Only advertise removal if the FS has already gone away or if no ticket
            ticket = self.get_ticket()
            if self.managedfilesystem_set.count() > 0 or ticket:
                excluded_states.append("removed")

            available_states = list(set(available_states) - set(excluded_states))
            return available_states

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def set_conf_params(self, params, new=True):
        """
        :param new: If False, do not increment the conf param version number, resulting in
                    new conf params not immediately being applied to the MGS (use if importing
                    records for an already configured filesystem).
        :param params: is a list of unsaved ConfParam objects"""
        version = None
        from django.db.models import F

        if new:
            ManagedMgs.objects.filter(pk=self.id).update(conf_param_version=F("conf_param_version") + 1)
        version = ManagedMgs.objects.get(pk=self.id).conf_param_version
        for p in params:
            p.version = version
            p.save()

    def target_type(self):
        return "mgs"

    def get_ticket(self):
        from chroma_core.models import MasterTicket

        tl = MasterTicket.objects.filter(mgs=self)
        return list(tl)[0].ticket if len(list(tl)) > 0 else None

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        # HYD-1089 should supercede these settings
        if settings.LUSTRE_MKFS_OPTIONS_MGS:
            mkfs_options = [settings.LUSTRE_MKFS_OPTIONS_MGS]

        return mkfs_options


class TargetRecoveryInfo(models.Model):
    """Record of what we learn from /sys/fs/lustre/*/*/recovery_status
    for a running target"""

    #: JSON-encoded dict parsed from /sys
    recovery_status = models.TextField()

    target = models.ForeignKey("chroma_core.ManagedTarget", on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @staticmethod
    @transaction.atomic
    def update(target, recovery_status):
        TargetRecoveryInfo.objects.filter(target=target).delete()
        instance = TargetRecoveryInfo.objects.create(target=target, recovery_status=json.dumps(recovery_status))
        return instance.is_recovering(recovery_status)

    def is_recovering(self, data=None):
        if not data:
            data = json.loads(self.recovery_status)
        return "status" in data and data["status"] == "RECOVERING"

    # def recovery_status_str(self):
    #    data = json.loads(self.recovery_status)
    #    if 'status' in data and data["status"] == "RECOVERING":
    #        return "%s %ss remaining" % (data["status"], data["time_remaining"])
    #    elif 'status' in data:
    #        return data["status"]
    #    else:
    #        return "N/A"


def _delete_target(target):
    if issubclass(target.downcast_class, ManagedMgs):
        from chroma_core.models.filesystem import ManagedFilesystem

        assert ManagedFilesystem.objects.filter(mgs=target).count() == 0

    target.mark_deleted()

    job_log.debug("_delete_target: %s %s" % (target, id(target)))


class ForgetTargetJob(StateChangeJob):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(
            stateful_object,
            {
                ManagedOst: help_text["remove_ost"],
                ManagedMdt: help_text["remove_mdt"],
                ManagedMgs: help_text["remove_mgt"],
            },
        )

    def description(self):
        modifier = "unmanaged" if self.target.immutable_state else "managed"
        return "Forget %s target %s" % (modifier, self.target)

    def get_requires_confirmation(self):
        return True

    def get_deps(self):
        deps = []
        if issubclass(self.target.downcast_class, ManagedMgs):
            mgs = self.target.downcast()
            ticket = mgs.get_ticket()
            if ticket:
                deps.append(DependOn(ticket, "forgotten", fix_state=ticket.state))

        return DependAll(deps)

    def on_success(self):
        _delete_target(self.target)

        super(ForgetTargetJob, self).on_success()

    state_transition = StateChangeJob.StateTransition(ManagedTarget, ["unmounted", "mounted"], "forgotten")
    stateful_object = "target"
    state_verb = "Forget"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)


class StartTargetJob(StateChangeJob):
    stateful_object = "target"
    state_transition = StateChangeJob.StateTransition(ManagedTarget, "unmounted", "mounted")
    state_verb = "Start"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(
            stateful_object,
            {
                ManagedOst: help_text["start_ost"],
                ManagedMgs: help_text["start_mgt"],
                ManagedMdt: help_text["start_mdt"],
            },
        )

    def description(self):
        return "Start target %s" % self.target

    def get_deps(self):
        if issubclass(self.target.downcast_class, ManagedMgs):
            ticket = self.target.downcast().get_ticket()
            if ticket:
                return DependAll(DependOn(ticket, "granted", fix_state="unmounted"))

        if self.target.downcast_class in [ManagedMdt, ManagedOst]:
            from chroma_core.models import FilesystemTicket

            target = self.target.downcast()

            ticket = FilesystemTicket.objects.filter(filesystem=target.filesystem_id).first()

            if ticket:
                return DependAll(DependOn(ticket.ticket, "granted", fix_state="unmounted"))

        deps = []

        # Depend on at least one targetmount having lnet up
        for host in self.target.hosts:
            from chroma_core.models import LNetConfiguration

            lnet_configuration = ObjectCache.get_one(LNetConfiguration, lambda l: l.host_id == host.id)
            deps.append(DependOn(lnet_configuration, "lnet_up", fix_state="unmounted"))

            try:
                pacemaker_configuration = ObjectCache.get_one(PacemakerConfiguration, lambda pm: pm.host_id == host.id)
                deps.append(DependOn(pacemaker_configuration, "started", fix_state="unmounted"))
            except PacemakerConfiguration.DoesNotExist:
                pass

        return DependAny(deps)

    def get_steps(self):
        return [(MountStep, {"fqdn": self.target.best_available_host().fqdn, "ha_label": self.target.ha_label})]


class MountStep(Step):
    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(kwargs["fqdn"], "ha_resource_start", kwargs["ha_label"])


class UnmountStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(kwargs["fqdn"], "ha_resource_stop", kwargs["ha_label"])


class StopTargetJob(StateChangeJob):
    stateful_object = "target"
    state_transition = StateChangeJob.StateTransition(ManagedTarget, "mounted", "unmounted")
    state_verb = "Stop"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)

    def get_requires_confirmation(self):
        return True

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(
            stateful_object,
            {ManagedOst: help_text["stop_ost"], ManagedMgs: help_text["stop_mgt"], ManagedMdt: help_text["stop_mdt"]},
        )

    def description(self):
        return "Stop target %s" % self.target

    def get_deps(self):
        if issubclass(self.target.downcast_class, ManagedMgs):
            ticket = self.target.downcast().get_ticket()
            if ticket:
                return DependAll(DependOn(ticket, "revoked", fix_state="mounted"))
        return super(StopTargetJob, self).get_deps()

    def get_steps(self):
        return [
            (UnmountStep, {"fqdn": self.target.best_available_host().fqdn, "ha_label": self.target.ha_label}),
        ]


class MigrateTargetJob(AdvertisedJob):
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)

    requires_confirmation = True

    classes = ["ManagedTarget"]

    class Meta:
        abstract = True
        app_label = "chroma_core"

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["migrate_target"]

    @classmethod
    def get_args(cls, target):
        return {"target_id": target.id}

    @classmethod
    def can_run(cls, instance):
        return False

    def create_locks(self):
        locks = super(MigrateTargetJob, self).create_locks()

        locks.append(
            StateLock(job=self, locked_item=self.target, begin_state="mounted", end_state="mounted", write=True)
        )

        return locks


class FailoverTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(
            kwargs["fqdn"], "ha_resource_move", [kwargs["ha_label"], kwargs["node_name"]]
        )


class FailoverTargetJob(MigrateTargetJob):
    verb = "Failover"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def can_run(cls, instance):
        if instance.immutable_state:
            return False

        return len(instance.inactive_hosts) > 0 and instance.active_host is not None

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["failover_target"]

    def description(self):
        return FailoverTargetJob.long_description(None)

    def get_deps(self):
        deps = [
            DependOn(self.target, "mounted"),
            DependOn(self.target.inactive_hosts[0].lnet_configuration, "lnet_up"),
        ]
        if self.target.inactive_hosts[0].pacemaker_configuration:
            deps.append(DependOn(self.target.inactive_hosts[0].pacemaker_configuration, "started"))
        return DependAll(deps)

    def on_success(self):
        # Persist the update to active_target_mount
        self.target.save()

    def get_steps(self):
        from chroma_core.lib.graphql import get_corosync_node_name_by_host_id

        host = self.target.inactive_hosts[0]

        node_name = get_corosync_node_name_by_host_id(host_id=host.id)

        return [
            (
                FailoverTargetStep,
                {"fqdn": host.fqdn, "ha_label": self.target.ha_label, "node_name": node_name},
            )
        ]

    @classmethod
    def get_confirmation(cls, instance):
        return """Forcibly migrate the target to its failover server. Clients attempting to access data on the target while the migration is occurring may experience delays until the migration completes."""


class TargetOfflineAlert(AlertStateBase):
    # When a target is offline, some or all files in the filesystem are inaccessible,
    # therefore the filesystem is considered not fully available, therefore it's ERROR.
    default_severity = logging.ERROR

    def alert_message(self):
        return "Target %s offline" % (self.alert_item)

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def end_event(self):
        return AlertEvent(
            message_str="%s started" % self.alert_item,
            alert_item=self.alert_item.first_known_host,
            alert=self,
            severity=logging.INFO,
        )

    def affected_targets(self, affect_target):
        affect_target(self.alert_item)


class TargetRecoveryAlert(AlertStateBase):
    # While a target is in recovery, the filesystem is still available, but I/O operations
    # from clients may block until recovery completes, effectively degrading performance.
    # Therefore it's WARNING.
    default_severity = logging.WARNING

    def alert_message(self):
        return "Target %s in recovery" % self.alert_item

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def end_event(self):
        return AlertEvent(
            message_str="Target '%s' completed recovery" % self.alert_item,
            alert_item=self.alert_item.active_host,
            alert=self,
            severity=logging.INFO,
        )

    def affected_targets(self, affect_target):
        affect_target(self.alert_item)


def get_host_targets(host_id):
    from chroma_core.lib.graphql import get_host_targets

    xs = [x["uuid"] for x in get_host_targets(host_id)]

    return ManagedTarget.objects.filter(uuid__in=xs, not_deleted=True)


def get_target_by_name(name):
    from chroma_core.lib.graphql import get_targets

    xs = get_targets()

    return next(x for x in xs if x["name"] == name)
