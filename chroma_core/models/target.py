# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import json
import re
import logging
import uuid
from collections import namedtuple
from chroma_core.lib.cache import ObjectCache

from django.db import models, transaction
from django.db.models import CASCADE
from chroma_core.lib.job import DependOn, DependAny, DependAll, Step, job_log
from chroma_core.models import AlertEvent
from chroma_core.models import AlertStateBase
from chroma_core.models import StateChangeJob, StateLock, AdvertisedJob
from chroma_core.models import ManagedHost, VolumeNode, Volume, HostContactAlert
from chroma_core.models import StatefulObject
from chroma_core.models import PacemakerConfiguration
from chroma_core.models import DeletableMetaclass, DeletableDowncastableMetaclass
from chroma_core.models import StonithNotEnabledAlert
from chroma_help.help import help_text
from iml_common.blockdevices.blockdevice import BlockDevice
from iml_common.filesystems.filesystem import FileSystem
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

    volume = models.ForeignKey("Volume", on_delete=CASCADE)

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

    def update_active_mount(self, nodename):
        """Set the active_mount attribute from the nodename of a host, raising
        RuntimeErrors if the host doesn't exist or doesn't have a ManagedTargetMount"""
        try:
            started_on = ObjectCache.get_one(ManagedHost, lambda mh: (mh.nodename == nodename) or (mh.fqdn == nodename))
        except ManagedHost.DoesNotExist:
            raise RuntimeError(
                "Target %s (%s) found on host %s, which is not a ManagedHost" % (self, self.id, nodename)
            )

        try:
            job_log.debug("Started %s on %s" % (self.ha_label, started_on))
            target_mount = ObjectCache.get_one(
                ManagedTargetMount, lambda mtm: mtm.target_id == self.id and mtm.host_id == started_on.id
            )
            self.active_mount = target_mount
        except ManagedTargetMount.DoesNotExist:
            job_log.error(
                "Target %s (%s) found on host %s (%s), which has no ManagedTargetMount for this self"
                % (self, self.id, started_on, started_on.pk)
            )
            raise RuntimeError(
                "Target %s reported as running on %s, but it is not configured there" % (self, started_on)
            )

    def get_param(self, key):
        params = self.targetparam_set.filter(key=key)
        return [p.value for p in params]

    def get_params(self):
        return [(p.key, p.value) for p in self.targetparam_set.all()]

    def get_failover_nids(self):
        fail_nids = []
        for secondary_mount in self.managedtargetmount_set.filter(primary=False):
            host = secondary_mount.host
            failhost_nids = host.lnet_configuration.get_nids()
            assert len(failhost_nids) != 0
            fail_nids.extend(failhost_nids)
        return fail_nids

    def nids(self):
        """Returns a tuple of per-host NID strings tuples"""
        host_nids = []
        # Note: order by -primary in order that the first argument passed to mkfs
        # in failover configurations is the primary mount -- Lustre will use the
        # first --mgsnode argument as the NID to connect to for target registration,
        # and if that is the secondary NID then bad things happen during first
        # filesystem start.
        for target_mount in self.managedtargetmount_set.all().order_by("-primary"):
            host = target_mount.host
            host_nids.append(tuple(host.lnet_configuration.get_nids()))

        return tuple(host_nids)

    @property
    def default_mount_point(self):
        return "/mnt/%s" % self.name

    @property
    def primary_host(self):
        try:
            """Getting all the hosts, and filtering in python is less db hits"""
            return next(mount.host for mount in self.managedtargetmount_set.all() if mount.primary)
        except StopIteration:
            error = "No primary host found for ManagedTarget %s" % self.name
            job_log.error(error)
            raise RuntimeError(error)

    @property
    def failover_hosts(self):
        """Getting all the hosts, and filtering in python is less db hits"""
        return [mount.host for mount in self.managedtargetmount_set.all() if not mount.primary]

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
    active_mount = models.ForeignKey("ManagedTargetMount", blank=True, null=True, on_delete=CASCADE)

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
        from chroma_core.models import ManagedFilesystem

        if not state:
            state = self.state

        deps = []
        if state == "mounted" and self.active_mount and not self.immutable_state:
            from chroma_core.models import LNetConfiguration

            # Depend on the active mount's host having LNet up, so that if
            # LNet is stopped on that host this target will be stopped first.
            target_mount = self.active_mount
            host = ObjectCache.get_one(ManagedHost, lambda mh: mh.id == target_mount.host_id)

            lnet_configuration = ObjectCache.get_by_id(LNetConfiguration, host.lnet_configuration.id)
            deps.append(DependOn(lnet_configuration, "lnet_up", fix_state="unmounted"))

            if host.pacemaker_configuration:
                pacemaker_configuration = ObjectCache.get_by_id(PacemakerConfiguration, host.pacemaker_configuration.id)
                deps.append(DependOn(pacemaker_configuration, "started", fix_state="unmounted"))

            # TODO: also express that this situation may be resolved by migrating
            # the target instead of stopping it.

        if issubclass(self.downcast_class, FilesystemMember) and state not in ["removed", "forgotten"]:
            # Make sure I follow if filesystem goes to 'removed'
            # or 'forgotten'
            # FIXME: should get filesystem membership from objectcache
            filesystem_id = self.downcast().filesystem_id
            filesystem = ObjectCache.get_by_id(ManagedFilesystem, filesystem_id)
            deps.append(
                DependOn(
                    filesystem,
                    "available",
                    acceptable_states=filesystem.not_states(["forgotten", "removed"]),
                    fix_state=lambda s: s,
                )
            )

        if state not in ["removed", "forgotten"]:
            from chroma_core.models import LNetConfiguration

            target_mounts = ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == self.id)
            for tm in target_mounts:
                host = ObjectCache.get_by_id(ManagedHost, tm.host_id)
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
        "ManagedTargetMount": lambda mtm: ObjectCache.mtm_targets(mtm.id),
        "ManagedHost": lambda mh: ObjectCache.host_targets(mh.id),
        "LNetConfiguration": lambda lc: ObjectCache.host_targets(lc.host.id),
        "PacemakerConfiguration": lambda pc: ObjectCache.host_targets(pc.host.id),
        "ManagedFilesystem": lambda mfs: ObjectCache.fs_targets(mfs.id),
        "Copytool": lambda ct: ObjectCache.client_mount_copytools(ct.id),
    }

    @classmethod
    @transaction.atomic
    def create_for_volume(cls_, volume_id, create_target_mounts=True, **kwargs):
        # Local imports to avoid inter-model import dependencies
        volume = Volume.objects.get(pk=volume_id)

        try:
            primary_volume_node = volume.volumenode_set.get(primary=True, host__not_deleted=True)

        except VolumeNode.DoesNotExist:
            raise RuntimeError("No primary lun_node exists for volume %s, cannot create target" % volume.id)
        except VolumeNode.MultipleObjectsReturned:
            raise RuntimeError("Multiple primary lun_nodes exist for volume %s, internal error" % volume.id)

        host = primary_volume_node.host
        corosync_configuration = host.corosync_configuration
        stonith_not_enabled = (
            len(StonithNotEnabledAlert.filter_by_item_id(corosync_configuration.__class__, corosync_configuration.id))
            > 0
        )

        if stonith_not_enabled:
            raise RuntimeError("Stonith not enabled for host %s, cannot create target" % host.fqdn)

        target = cls_(**kwargs)
        target.volume = volume

        # Acquire a target index for FilesystemMember targets, and populate `name`
        if issubclass(cls_, FilesystemMember):
            # Make sure we update the value in the object cache, not just the value in the DB. HYD-4898
            filesystem = ObjectCache.get_by_id(type(target.filesystem), target.filesystem.id)

            if issubclass(cls_, ManagedMdt):
                target_index = filesystem.mdt_next_index
                target_name = "%s-MDT%04x" % (filesystem.name, target_index)
                filesystem.mdt_next_index += 1
            elif issubclass(cls_, ManagedOst):
                target_index = filesystem.ost_next_index
                target_name = "%s-OST%04x" % (filesystem.name, target_index)
                filesystem.ost_next_index += 1
            else:
                raise RuntimeError("Unknown filesystem member type %s" % type(cls_))

            target.name = target_name
            target.index = target_index
            filesystem.save()
            filesystem = ObjectCache.update(filesystem)
        else:
            target.name = "MGS"

        target.save()

        target_mounts = []

        def create_target_mount(volume_node):
            mount = ManagedTargetMount(
                volume_node=volume_node,
                target=target,
                host=volume_node.host,
                mount_point=target.default_mount_point,
                primary=volume_node.primary,
            )
            mount.save()
            target_mounts.append(mount)

        if create_target_mounts:
            create_target_mount(primary_volume_node)

            for secondary_volume_node in volume.volumenode_set.filter(use=True, primary=False, host__not_deleted=True):
                create_target_mount(secondary_volume_node)

        return target, target_mounts

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

    @classmethod
    def get_by_host(cls, host):
        return cls.objects.get(managedtargetmount__host=host)

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


class RemoveConfiguredTargetJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(ManagedTarget, "unmounted", "removed")
    stateful_object = "target"
    state_verb = "Remove"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)

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

    def get_requires_confirmation(self):
        return True

    def get_confirmation_string(self):
        return select_description(
            self.target,
            {
                ManagedOst: help_text["remove_ost"],
                ManagedMdt: help_text["remove_mdt"],
                ManagedMgs: help_text["remove_mgt"],
            },
        )

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def description(self):
        return help_text["remove_target_XXXX_from_filesystem"] % self.target

    def get_steps(self):
        # TODO: actually do something with Lustre before deleting this from our DB
        steps = []
        for target_mount in self.target.managedtargetmount_set.all().order_by("primary"):
            steps.append(
                (
                    RemoveTargetFromPacemakerConfigStep,
                    {"target_mount": target_mount, "target": target_mount.target, "host": target_mount.host},
                )
            )
        for target_mount in self.target.managedtargetmount_set.all().order_by("primary"):
            steps.append(
                (
                    UnconfigureTargetStoreStep,
                    {"target_mount": target_mount, "target": target_mount.target, "host": target_mount.host},
                )
            )
        return steps

    def on_success(self):
        _delete_target(self.target)
        super(RemoveConfiguredTargetJob, self).on_success()


# HYD-832: when transitioning from 'registered' to 'removed', do something to
# remove this target from the MGS
class RemoveTargetJob(StateChangeJob):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    state_transition = StateChangeJob.StateTransition(
        ManagedTarget, ["unformatted", "formatted", "registered"], "removed"
    )
    stateful_object = "target"
    state_verb = "Remove"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)

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
        return help_text["remove_target_XXXX_from_filesystem"] % self.target

    def get_confirmation_string(self):
        if self.target.state == "registered":
            return select_description(
                self.target,
                {
                    ManagedOst: help_text["remove_ost"],
                    ManagedMdt: help_text["remove_mdt"],
                    ManagedMgs: help_text["remove_mgt"],
                },
            )

        else:
            return None

    def get_requires_confirmation(self):
        return True

    def on_success(self):
        mounts = ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target.id == self.target.id)

        _delete_target(self.target)

        for m in mounts:
            m.mark_deleted()
            m.save()

        super(RemoveTargetJob, self).on_success()


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
        mounts = ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target.id == self.target.id)

        _delete_target(self.target)

        for m in mounts:
            m.mark_deleted()
            m.save()

        super(ForgetTargetJob, self).on_success()

    state_transition = StateChangeJob.StateTransition(ManagedTarget, ["unmounted", "mounted"], "forgotten")
    stateful_object = "target"
    state_verb = "Forget"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)


class RegisterTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]

        result = self.invoke_agent(
            kwargs["primary_host"],
            "register_target",
            {
                "device_path": kwargs["device_path"],
                "mount_point": kwargs["mount_point"],
                "backfstype": kwargs["backfstype"],
            },
        )

        if not result["label"] == target.name:
            # We synthesize a target name (e.g. testfs-OST0001) when creating targets, then
            # pass --index to mkfs.lustre, so our name should match what is set after registration
            raise RuntimeError(
                "Registration returned unexpected target name '%s' (expected '%s')" % (result["label"], target.name)
            )
        job_log.debug(
            "Registration complete, updating target %d with name=%s, ha_label=%s"
            % (target.id, target.name, target.ha_label)
        )


class GenerateHaLabelStep(Step):
    idempotent = True

    def sanitize_name(self, name):
        FILTER_REGEX = r"^\d|^-|^\.|[(){}[\].:@$%&/+,;\s]+"
        sanitized_name = re.sub(FILTER_REGEX, "_", name)
        return "%s_%s" % (sanitized_name, uuid.uuid4().hex[:6])

    def run(self, kwargs):
        target = kwargs["target"]
        target.ha_label = self.sanitize_name(target.name)
        job_log.debug("Generated ha_label=%s for target %s (%s)" % (target.ha_label, target.id, target.name))


class OpenLustreFirewallStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(
            kwargs["host"],
            "open_firewall",
            {"port": 988, "address": None, "proto": "tcp", "description": "lustre", "persist": True},
        )

    @classmethod
    def describe(cls, kwargs):
        return help_text["opening_lustre_firewall_port"] % kwargs["host"]


class ConfigureTargetStoreStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]
        target_mount = kwargs["target_mount"]
        volume_node = kwargs["volume_node"]
        host = kwargs["host"]
        backfstype = kwargs["backfstype"]
        device_type = kwargs["device_type"]

        assert volume_node is not None

        self.invoke_agent(
            host,
            "configure_target_store",
            {
                "device": volume_node.path,
                "uuid": target.uuid,
                "mount_point": target_mount.mount_point,
                "backfstype": backfstype,
                "device_type": device_type,
            },
        )


class UnconfigureTargetStoreStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]
        host = kwargs["host"]

        self.invoke_agent(host, "unconfigure_target_store", {"uuid": target.uuid})


class AddTargetToPacemakerConfigStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]
        target_mount = kwargs["target_mount"]
        volume_node = kwargs["volume_node"]
        host = kwargs["host"]

        assert volume_node is not None

        self.invoke_agent_expect_result(
            host,
            "configure_target_ha",
            {
                "device": volume_node.path,
                "ha_label": target.ha_label,
                "uuid": target.uuid,
                "primary": target_mount.primary,
                "mount_point": target_mount.mount_point,
            },
        )

    @classmethod
    def describe(cls, kwargs):
        return help_text["add_target_to_pacemaker_config"] % kwargs["target"]


class RemoveTargetFromPacemakerConfigStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]
        target_mount = kwargs["target_mount"]

        self.invoke_agent_expect_result(
            kwargs["host"],
            "unconfigure_target_ha",
            {"ha_label": target.ha_label, "uuid": target.uuid, "primary": target_mount.primary},
        )

    @classmethod
    def describe(cls, kwargs):
        return help_text["remove_target_from_pacemaker_config"] % kwargs["target"]


TargetVolumeInfo = namedtuple("TargetVolumeInfo", ["host", "path", "device_type"])


class MountOrImportStep(Step):
    """
    When carrying out operations we need to make sure a Target is mounted on the correct node. This is often (probably)
    always pre or post HA operation. For example when formatting the device we need to be sure it is where we are going
    to carry out the format command.

    Three parameters
    target: The target in question, this allows a good user message.
    inactive_volume_nodes: Is the volume_nodes that are not active on.
    active_volume_node: Is the volume_nodes that are active on.

    These parameters can be created using the create_parameters function, which allows the more complex building
    functionality to lie within the Step code but without the run itself requiring database access.

    Note that this Method will fail if the desired volume is not imported (zfs) on an available host as then there
    will be no relevant VolumeNodes!
    """

    idempotent = True

    def inactivate_volume_node(self, volume_node):
        # If the node cannot be contacted then this is not a failure, because the node might be broken, it is refuses
        # to export the node that is an error.
        # The first is not an issue because after doing this export we will only do a soft import and so will fail if
        # something sill have the node imported.
        from chroma_core.services.job_scheduler.agent_rpc import AgentException
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpcMessenger

        try:
            self.invoke_agent_expect_result(
                volume_node.host, "export_target", {"device_type": volume_node.device_type, "path": volume_node.path}
            )
        except AgentException as e:
            # TODO: When landing this on b4_0 for future code we will add a new exception AgentContactException to
            # deal with this case properly
            if e.backtrace.startswith(AgentRpcMessenger.COULD_NOT_CONTACT_TAG) is False:
                raise

    def run(self, kwargs):
        threads = []

        for inactive_volume_node in kwargs["inactive_volume_nodes"]:
            thread = util.ExceptionThrowingThread(target=self.inactivate_volume_node, args=(inactive_volume_node,))
            thread.start()
            threads.append(thread)

        # This will raise an exception if any of the threads raise an exception
        util.ExceptionThrowingThread.wait_for_threads(threads)

        if kwargs["active_volume_node"] is None:
            device_type = kwargs["target"].volume.filesystem_type
            # in the case that the volume node is missing, attempt to import target volume
            self.invoke_agent_expect_result(
                kwargs["host"],
                "import_target",
                {
                    "device_type": ("linux" if device_type in ["ext4", "mpath_member", ""] else device_type),
                    "path": kwargs["target"].volume.label,
                    "pacemaker_ha_operation": False,
                },
            )
        else:
            self.invoke_agent_expect_result(
                kwargs["active_volume_node"].host,
                "import_target",
                {
                    "device_type": kwargs["active_volume_node"].device_type,
                    "path": kwargs["active_volume_node"].path,
                    "pacemaker_ha_operation": False,
                },
            )

        if kwargs["start_target"] is True:
            result = self.invoke_agent_expect_result(
                kwargs["host"], "start_target", {"ha_label": kwargs["target"].ha_label}
            )

            kwargs["target"].update_active_mount(result)

    @classmethod
    def describe(cls, kwargs):
        if kwargs["active_volume_node"] is None:
            return help_text["export_target_from_nodes"] % kwargs["target"]
        else:
            if kwargs["start_target"] is True:
                return help_text["mounting_target_on_node"] % (kwargs["target"], kwargs["active_volume_node"].host)
            else:
                return help_text["moving_target_to_node"] % (kwargs["target"], kwargs["active_volume_node"].host)

    @classmethod
    def create_parameters(cls, target, host, start_target):
        """
        Create the kwargs appropriate for the MakeTargetActive step.

        :param target: The lustre target to be made available to host (and hence unavailable to other hosts)
        :param host: The host target to be made available to
        :param start_target: True means the target is started False means it is just imported.
        :return:
        """
        assert host is not None

        inactive_volume_nodes = []
        active_volume_node = None

        for volume_node in target.volume.volumenode_set.all():
            target_volume_info = TargetVolumeInfo(
                volume_node.host,
                volume_node.path,
                volume_node.volume.storage_resource.to_resource_class().device_type(),
            )

            if host == volume_node.host:
                active_volume_node = target_volume_info
            else:
                inactive_volume_nodes.append(target_volume_info)

        job_log.info("create_parameters: host: '%s' active_volume_node: '%s'" % (host, active_volume_node))

        return {
            "target": target,
            "host": host,
            "inactive_volume_nodes": inactive_volume_nodes,
            "active_volume_node": active_volume_node,
            "start_target": start_target,
        }


class ConfigureTargetJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(ManagedTarget, "registered", "unmounted")
    stateful_object = "target"
    state_verb = "Configure mount points"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_target"]

    def description(self):
        return "Configure %s mount points" % self.target

    def get_steps(self):
        steps = []

        target_mounts = list(self.target.managedtargetmount_set.all().order_by("-primary"))

        for target_mount in target_mounts:
            steps.append((OpenLustreFirewallStep, {"host": target_mount.host}))

        for target_mount in target_mounts:
            device_type = target_mount.volume_node.volume.storage_resource.to_resource_class().device_type()
            # retrieve the preferred fs type for this block device type to be used as backfstype for target
            backfstype = BlockDevice(device_type, target_mount.volume_node.path).preferred_fstype

            steps.append(
                (
                    ConfigureTargetStoreStep,
                    {
                        "host": target_mount.host,
                        "target": target_mount.target,
                        "target_mount": target_mount,
                        "backfstype": backfstype,
                        "volume_node": target_mount.volume_node,
                        "device_type": target_mount.target.volume.storage_resource.to_resource_class().device_type(),
                    },
                )
            )

        for target_mount in target_mounts:
            steps.append(
                (
                    AddTargetToPacemakerConfigStep,
                    {
                        "host": target_mount.host,
                        "target": target_mount.target,
                        "target_mount": target_mount,
                        "volume_node": target_mount.volume_node,
                    },
                )
            )

        return steps

    def get_deps(self):
        deps = []

        prim_mtm = ObjectCache.get_one(
            ManagedTargetMount, lambda mtm: mtm.primary is True and mtm.target_id == self.target.id
        )
        deps.append(DependOn(prim_mtm.host.lnet_configuration, "lnet_up"))

        for target_mount in self.target.managedtargetmount_set.all().order_by("-primary"):
            deps.append(DependOn(target_mount.host.pacemaker_configuration, "started"))

        return DependAll(deps)


class RegisterTargetJob(StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = StateChangeJob.StateTransition(ManagedTarget, "formatted", "registered")
    stateful_object = "target"
    state_verb = "Register"
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["register_target"]

    def description(self):
        return "Register %s" % self.target

    def get_steps(self):
        steps = []

        target_class = self.target.downcast_class
        if issubclass(target_class, ManagedMgs):
            steps = []
        elif issubclass(target_class, FilesystemMember):
            primary_mount = self.target.managedtargetmount_set.get(primary=True)
            path = primary_mount.volume_node.path

            mgs_id = self.target.downcast().filesystem.mgs.id
            mgs = ObjectCache.get_by_id(ManagedTarget, mgs_id)

            # retrieve the preferred fs type for this block device type to be used as backfstype for target
            device_type = primary_mount.volume_node.volume.storage_resource.to_resource_class().device_type()
            backfstype = BlockDevice(device_type, primary_mount.volume_node.path).preferred_fstype

            # Check that the active mount of the MGS is its primary mount (HYD-233 Lustre limitation)
            if not mgs.active_mount == mgs.managedtargetmount_set.get(primary=True):
                raise RuntimeError("Cannot register target while MGS is not started on its primary server")

            steps = [
                (
                    RegisterTargetStep,
                    {
                        "primary_host": primary_mount.host,
                        "target": self.target,
                        "device_path": path,
                        "mount_point": primary_mount.mount_point,
                        "backfstype": backfstype,
                    },
                )
            ]
        else:
            raise NotImplementedError(target_class)

        steps.append((GenerateHaLabelStep, {"target": self.target}))

        return steps

    def get_deps(self):
        deps = []

        deps.append(DependOn(ObjectCache.target_primary_server(self.target).lnet_configuration, "lnet_up"))

        if issubclass(self.target.downcast_class, FilesystemMember):
            # FIXME: spurious downcast, should cache filesystem associaton in objectcache
            mgs = ObjectCache.get_by_id(ManagedTarget, self.target.downcast().filesystem.mgs_id)

            deps.append(DependOn(mgs, "mounted"))

        if issubclass(self.target.downcast_class, ManagedOst):
            # FIXME: spurious downcast, should cache filesystem associaton in objectcache
            filesystem_id = self.target.downcast().filesystem_id
            mdts = ObjectCache.get(
                ManagedTarget,
                lambda target: issubclass(target.downcast_class, ManagedMdt)
                and target.downcast().filesystem_id == filesystem_id,
            )

            for mdt in mdts:
                deps.append(DependOn(mdt, "mounted"))

        return DependAll(deps)


class MountStep(Step):
    """
    This is a defunct step and should not be used for anything. Steps cannot be deleted from the
    source because Picklefield is used for the XXX field and unPickling requires all types that
    were present at the time of Pickling are present at the time of unPickling. Migrating the Pickles
    would be very difficult.
    """

    pass


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

        deps = []
        # Depend on at least one targetmount having lnet up
        mtms = ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == self.target_id)
        for target_mount in mtms:
            from chroma_core.models import LNetConfiguration

            lnet_configuration = ObjectCache.get_one(LNetConfiguration, lambda l: l.host_id == target_mount.host_id)
            deps.append(DependOn(lnet_configuration, "lnet_up", fix_state="unmounted"))

            try:
                pacemaker_configuration = ObjectCache.get_one(
                    PacemakerConfiguration, lambda pm: pm.host_id == target_mount.host_id
                )
                deps.append(DependOn(pacemaker_configuration, "started", fix_state="unmounted"))
            except PacemakerConfiguration.DoesNotExist:
                pass

        return DependAny(deps)

    def get_steps(self):
        device_type = self.target.volume.filesystem_type
        return [
            (
                MountOrImportStep,
                MountOrImportStep.create_parameters(self.target, self.target.best_available_host(), False),
            ),
            (
                UpdateManagedTargetMount,
                {
                    "target": self.target,
                    "device_type": ("linux" if device_type in ["ext4", "mpath_member", ""] else device_type),
                },
            ),
            (
                MountOrImportStep,
                MountOrImportStep.create_parameters(self.target, self.target.best_available_host(), True),
            ),
        ]


class UnmountStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]

        self.invoke_agent_expect_result(kwargs["host"], "stop_target", {"ha_label": target.ha_label})
        target.active_mount = None


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
        # Update MTMs before attempting to stop/unmount
        device_type = self.target.volume.filesystem_type
        return [
            (
                UpdateManagedTargetMount,
                {
                    "target": self.target,
                    "device_type": ("linux" if device_type in ["ext4", "mpath_member", ""] else device_type),
                },
            ),
            (UnmountStep, {"target": self.target, "host": self.target.best_available_host()}),
        ]


class PreFormatCheck(Step):
    @classmethod
    def describe(cls, kwargs):
        return "Prepare for format %s:%s" % (kwargs["host"], kwargs["path"])

    def run(self, kwargs):
        self.invoke_agent_expect_result(
            kwargs["host"], "check_block_device", {"path": kwargs["path"], "device_type": kwargs["device_type"]}
        )


class PreFormatComplete(Step):
    """
    This step separated from PreFormatCheck so that it
    can write to the database without forcing the remote
    ops in the check to hold a DB connection (would limit
    parallelism).
    """

    database = True

    def run(self, kwargs):
        job_log.info("%s passed pre-format check, allowing subsequent reformats" % kwargs["target"])
        with transaction.atomic():
            kwargs["target"].reformat = True
            kwargs["target"].save()


class MkfsStep(Step):
    database = True

    def _mkfs_args(self, kwargs):
        target = kwargs["target"]

        mkfs_args = {}

        mkfs_args["target_types"] = target.downcast().target_type()
        mkfs_args["target_name"] = target.name

        if issubclass(target.downcast_class, FilesystemMember):
            mkfs_args["fsname"] = target.downcast().filesystem.name
            mkfs_args["mgsnode"] = kwargs["mgs_nids"]

        if kwargs["reformat"]:
            mkfs_args["reformat"] = True

        if kwargs["failover_nids"]:
            mkfs_args["failnode"] = kwargs["failover_nids"]

        mkfs_args["device"] = kwargs["device_path"]
        if issubclass(target.downcast_class, FilesystemMember):
            mkfs_args["index"] = target.downcast().index

        mkfs_args["device_type"] = kwargs["device_type"]
        mkfs_args["backfstype"] = kwargs["backfstype"]

        if len(kwargs["mkfsoptions"]) > 0:
            mkfs_args["mkfsoptions"] = " ".join(kwargs["mkfsoptions"])

        return mkfs_args

    @classmethod
    def describe(cls, kwargs):
        target = kwargs["target"]
        target_mount = target.managedtargetmount_set.get(primary=True)
        return "Format %s on %s" % (target, target_mount.host)

    def run(self, kwargs):
        target = kwargs["target"]

        args = self._mkfs_args(kwargs)
        result = self.invoke_agent(kwargs["primary_host"], "format_target", args)

        if not (result["filesystem_type"] in FileSystem.all_supported_filesystems()):
            raise RuntimeError("Unexpected filesystem type '%s'" % result["filesystem_type"])

        target.uuid = result["uuid"]

        if result["filesystem_type"] != "zfs":
            target.volume.filesystem_type = result["filesystem_type"]

            if result["inode_count"] is not None:
                # Check that inode_size was applied correctly
                if target.inode_size:
                    if target.inode_size != result["inode_size"]:
                        raise RuntimeError(
                            "Failed for format target with inode size %s, actual inode size %s"
                            % (target.inode_size, result["inode_size"])
                        )

                # Check that inode_count was applied correctly
                if target.inode_count:
                    if target.inode_count != result["inode_count"]:
                        raise RuntimeError(
                            "Failed for format target with inode count %s, actual inode count %s"
                            % (target.inode_count, result["inode_count"])
                        )

                # NB cannot check that bytes_per_inode was applied correctly as that setting is not stored in the FS
                target.inode_count = result["inode_count"]
                target.inode_size = result["inode_size"]

            target.volume.save()

        target.save()


class UpdateManagedTargetMount(Step):
    """
    This step will update the volume and volume_node relationships with
    manage target mounts and managed targets to reflect changes during
    MkfsStep and device mounting/unmounting.
    """

    database = True

    @classmethod
    def describe(cls, kwargs):
        return "Update managed target mounts for target %s" % kwargs["target"]

    def run(self, kwargs):
        target = kwargs["target"]
        device_type = kwargs["device_type"]
        job_log.info("Updating mtm volume_nodes for target %s" % target)

        for mtm in target.managedtargetmount_set.all():
            host = mtm.host
            current_volume_node = mtm.volume_node

            # represent underlying zpool as blockdevice if path is zfs dataset
            # todo: move this constraint into BlockDeviceZfs class
            block_device = BlockDevice(
                device_type,
                current_volume_node.path.split("/")[0] if device_type == "zfs" else current_volume_node.path,
            )

            filesystem = FileSystem(block_device.preferred_fstype, block_device.device_path)
            job_log.info("Looking for volume_nodes for host %s , path %s" % (host, filesystem.mount_path(target.name)))
            job_log.info("Current volume_nodes for host %s = %s" % (host, VolumeNode.objects.filter(host=host)))

            mtm.volume_node = util.wait_for_result(
                lambda: VolumeNode.objects.get(host=host, path=filesystem.mount_path(target.name)),
                logger=job_log,
                timeout=60 * 10,
                expected_exception_classes=[VolumeNode.DoesNotExist],
            )

            mtm.volume_node.primary = current_volume_node.primary
            mtm.volume_node.save()
            mtm.save()

            target.volume = mtm.volume_node.volume

        target.save()


class FormatTargetJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(ManagedTarget, "unformatted", "formatted")
    target = models.ForeignKey(ManagedTarget, on_delete=CASCADE)
    stateful_object = "target"
    state_verb = "Format"
    cancellable = False

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["format_target"]

    def description(self):
        return "Format %s" % self.target

    def get_deps(self):
        from chroma_core.models import ManagedFilesystem

        deps = []

        hosts = set()
        for tm in ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == self.target_id):
            hosts.add(tm.host)

        for host in hosts:
            deps.append(DependOn(host.lnet_configuration, "lnet_up"))

        if issubclass(self.target.downcast_class, FilesystemMember):
            # FIXME: spurious downcast, should use ObjectCache to remember which targets are in
            # which filesystem
            filesystem = ObjectCache.get_by_id(ManagedFilesystem, self.target.downcast().filesystem_id)
            mgt_id = filesystem.mgs_id

            mgs_hosts = set()
            for tm in ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == mgt_id):
                mgs_hosts.add(tm.host)

            for host in mgs_hosts:
                deps.append(DependOn(host.lnet_configuration, "lnet_up"))

        return DependAll(deps)

    def get_steps(self):
        primary_mount = self.target.managedtargetmount_set.get(primary=True)

        if issubclass(self.target.downcast_class, FilesystemMember):
            # FIXME: spurious downcast, should use ObjectCache to remember which targets are in
            # which filesystem
            mgs_nids = self.target.downcast().filesystem.mgs.nids()
        else:
            mgs_nids = None

        device_type = self.target.volume.storage_resource.to_resource_class().device_type()

        steps = [(MountOrImportStep, MountOrImportStep.create_parameters(self.target, primary_mount.host, False))]

        if not self.target.reformat:
            # We are not expecting to need to reformat/overwrite this volume
            # so before proceeding, check that it is indeed unoccupied
            steps.extend(
                [
                    (
                        PreFormatCheck,
                        {
                            "host": primary_mount.host,
                            "path": primary_mount.volume_node.path,
                            "device_type": device_type,
                        },
                    ),
                    (PreFormatComplete, {"target": self.target}),
                ]
            )

        # This line is key, because it causes the volume property to be filled so it can be access by the step
        self.target.volume

        block_device = BlockDevice(device_type, primary_mount.volume_node.path)
        filesystem = FileSystem(block_device.preferred_fstype, primary_mount.volume_node.path)

        mkfsoptions = filesystem.mkfs_options(self.target)

        mkfsoptions = self.target.downcast().mkfs_override_options(block_device.preferred_fstype, mkfsoptions)

        steps.extend(
            [
                (
                    MkfsStep,
                    {
                        "primary_host": primary_mount.host,
                        "target": self.target,
                        "device_path": primary_mount.volume_node.path,
                        "failover_nids": self.target.get_failover_nids(),
                        "mgs_nids": mgs_nids,
                        "reformat": self.target.reformat,
                        "device_type": device_type,
                        "backfstype": block_device.preferred_fstype,
                        "mkfsoptions": mkfsoptions,
                    },
                ),
                (UpdateManagedTargetMount, {"target": self.target, "device_type": device_type}),
            ]
        )

        return steps

    def on_success(self):
        super(FormatTargetJob, self).on_success()
        self.target.volume.save()

    def create_locks(self):
        locks = super(FormatTargetJob, self).create_locks()

        # Take a write lock on mtm objects related to this target
        for mtm in self.target.managedtargetmount_set.all():
            job_log.debug("Creating StateLock on %s/%s" % (mtm.__class__, mtm.id))
            locks.append(StateLock(job=self, locked_item=mtm, write=True))

        return locks


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


class FailbackTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]
        self.invoke_agent_expect_result(kwargs["host"], "failback_target", {"ha_label": kwargs["target"].ha_label})
        target.active_mount = kwargs["primary_mount"]


class FailbackTargetJob(MigrateTargetJob):
    verb = "Failback"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def can_run(cls, instance):
        if instance.immutable_state:
            return False

        return (
            len(instance.failover_hosts) > 0
            and instance.active_host is not None
            and instance.primary_host != instance.active_host
        )
        # HYD-1238: once we have a valid online/offline piece of info for each host,
        # reinstate the condition
        # instance.primary_host.is_available()

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["failback_target"]

    def description(self):
        return FailbackTargetJob.long_description(None)

    def get_deps(self):
        deps = [
            DependOn(self.target, "mounted"),
            DependOn(self.target.primary_host.lnet_configuration, "lnet_up"),
        ]
        if self.target.primary_host.pacemaker_configuration:
            deps.append(DependOn(self.target.primary_host.pacemaker_configuration, "started"))
        return DependAll(deps)

    def on_success(self):
        # Persist the update to active_target_mount
        self.target.save()

    def get_steps(self):
        return [
            (
                FailbackTargetStep,
                {
                    "target": self.target,
                    "host": self.target.primary_host,
                    "primary_mount": self.target.managedtargetmount_set.get(primary=True),
                },
            )
        ]

    @classmethod
    def get_confirmation(cls, instance):
        return """Migrate the target back to its primary server. Clients attempting to access data on the target while the migration is occurring may experience delays until the migration completes."""


class FailoverTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs["target"]
        self.invoke_agent_expect_result(kwargs["host"], "failover_target", {"ha_label": kwargs["target"].ha_label})
        target.active_mount = kwargs["secondary_mount"]


class FailoverTargetJob(MigrateTargetJob):
    verb = "Failover"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def can_run(cls, instance):
        if instance.immutable_state:
            return False

        return len(instance.failover_hosts) > 0 and instance.primary_host == instance.active_host

    # HYD-1238: once we have a valid online/offline piece of info for each host,
    # reinstate the condition
    #                instance.failover_hosts[0].is_available() and \

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["failover_target"]

    def description(self):
        return FailoverTargetJob.long_description(None)

    def get_deps(self):
        deps = [
            DependOn(self.target, "mounted"),
            DependOn(self.target.failover_hosts[0].lnet_configuration, "lnet_up"),
        ]
        if self.target.failover_hosts[0].pacemaker_configuration:
            deps.append(DependOn(self.target.failover_hosts[0].pacemaker_configuration, "started"))
        return DependAll(deps)

    def on_success(self):
        # Persist the update to active_target_mount
        self.target.save()

    def get_steps(self):
        host = self.target.failover_hosts[0]

        return [
            (
                FailoverTargetStep,
                {
                    "target": self.target,
                    "host": host,
                    "secondary_mount": self.target.managedtargetmount_set.get(primary=False, host=host),
                },
            )
        ]

    @classmethod
    def get_confirmation(cls, instance):
        return """Forcibly migrate the target to its failover server. Clients attempting to access data on the target while the migration is occurring may experience delays until the migration completes."""


class ManagedTargetMount(models.Model):
    """Associate a particular Lustre target with a device node on a host"""

    __metaclass__ = DeletableMetaclass

    # FIXME: both VolumeNode and TargetMount refer to the host
    host = models.ForeignKey("ManagedHost", on_delete=CASCADE)
    mount_point = models.CharField(max_length=512, null=True, blank=True)
    volume_node = models.ForeignKey("VolumeNode", on_delete=CASCADE)
    primary = models.BooleanField(default=False)
    target = models.ForeignKey("ManagedTarget", on_delete=CASCADE)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # If primary is true, then target must be unique
        if self.primary:
            from django.db.models import Q

            other_primaries = ManagedTargetMount.objects.filter(~Q(id=self.id), target=self.target, primary=True)
            if other_primaries.count() > 0:
                from django.core.exceptions import ValidationError

                raise ValidationError("Cannot have multiple primary mounts for target %s" % self.target)

        # If this is an MGS, there may not be another MGS on
        # this host
        if issubclass(self.target.downcast_class, ManagedMgs):
            from django.db.models import Q

            other_mgs_mountables_local = ManagedTargetMount.objects.filter(
                ~Q(id=self.id), target__in=ManagedMgs.objects.all(), host=self.host
            ).count()
            if other_mgs_mountables_local > 0:
                from django.core.exceptions import ValidationError

                raise ValidationError("Cannot have multiple MGS mounts on host %s" % self.host.address)

        return super(ManagedTargetMount, self).save(force_insert, force_update, using, update_fields)

    def device(self):
        return self.volume_node.path

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def __str__(self):
        if self.primary:
            kind_string = "primary"
        elif not self.volume_node:
            kind_string = "failover_nodev"
        else:
            kind_string = "failover"

        return "%s:%s:%s" % (self.host, kind_string, self.target)


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
            alert_item=self.alert_item.primary_host,
            alert=self,
            severity=logging.INFO,
        )

    def affected_targets(self, affect_target):
        affect_target(self.alert_item)


class TargetFailoverAlert(AlertStateBase):
    # The filesystem should remain available while a target is failed over, but
    # performance may be degraded, therefore it's worse than INFO, but not as bad as ERROR.
    default_severity = logging.WARNING

    def alert_message(self):
        return "Target %s running on secondary server" % self.alert_item

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def end_event(self):
        return AlertEvent(
            message_str="%s failover unmounted" % self.alert_item,
            alert_item=self.alert_item.primary_host,
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
            alert_item=self.alert_item.primary_host,
            alert=self,
            severity=logging.INFO,
        )

    def affected_targets(self, affect_target):
        affect_target(self.alert_item)


def get_target_by_name(name):
    from chroma_core.lib.graphql import get_targets

    xs = get_targets()

    return next(x for x in xs if x["name"] == name)
