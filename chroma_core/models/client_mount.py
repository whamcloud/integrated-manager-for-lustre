# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models

from chroma_core.lib.cache import ObjectCache
from chroma_core.models.utils import CHARFIELD_MAX_LENGTH
from chroma_core.models.host import ManagedHost, HostOfflineAlert, HostContactAlert
from chroma_core.models.jobs import DeletableStatefulObject
from chroma_core.models.jobs import StateChangeJob
from chroma_core.models.alert import AlertState
from chroma_core.models.jobs import Job, AdvertisedJob
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_help.help import help_text


class LustreClientMount(DeletableStatefulObject):
    host = models.ForeignKey("ManagedHost", help_text="Mount host", related_name="client_mounts")
    filesystem = models.ForeignKey("ManagedFilesystem", help_text="Mounted filesystem")
    mountpoint = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, help_text="Filesystem mountpoint on host", null=True, blank=True
    )

    states = ["unmounted", "mounted", "removed"]
    initial_state = "unmounted"

    def __str__(self):
        return self.get_label()

    @property
    def active(self):
        return self.state == "mounted"

    def get_label(self):
        return "%s:%s (%s)" % (self.host, self.mountpoint, self.state)

    def get_deps(self, state=None):
        if not state:
            state = self.state

        deps = []
        if state == "mounted":
            # Depend on this mount's host having LNet up. If LNet is stopped
            # on the host, this filesystem will be unmounted first.
            deps.append(DependOn(self.host.lnet_configuration, "lnet_up", fix_state="unmounted"))

        if state != "removed":
            # Depend on the fs being available.
            deps.append(DependOn(self.filesystem, "available", fix_state="unmounted"))

            # But if either the host or the filesystem are removed, the
            # mount should follow.
            deps.append(
                DependOn(
                    self.host,
                    "lnet_up",
                    acceptable_states=list(set(self.host.states) - set(["removed", "forgotten"])),
                    fix_state="removed",
                )
            )
            deps.append(
                DependOn(
                    self.filesystem,
                    "available",
                    acceptable_states=list(set(self.filesystem.states) - set(["removed", "forgotten"])),
                    fix_state="removed",
                )
            )

        return DependAll(deps)

    reverse_deps = {
        "ManagedHost": lambda mh: ObjectCache.host_client_mounts(mh.id),
        "LNetConfiguration": lambda lc: ObjectCache.host_client_mounts(lc.host.id),
        "ManagedFilesystem": lambda mf: ObjectCache.filesystem_client_mounts(mf.id),
    }

    class Meta:
        app_label = "chroma_core"
        unique_together = ("host", "filesystem")


class MountLustreFilesystemsStep(Step):
    """
    Does the dirty work of mounting the list of supplied
    filesystems on a host. Used by both state change jobs
    and advertised jobs.
    """

    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        filesystems = kwargs["filesystems"]
        self.invoke_agent(host, "mount_lustre_filesystems", {"filesystems": filesystems})


class UnmountLustreFilesystemsStep(Step):
    """
    Does the dirty work of unmounting the list of supplied
    filesystems on a host. Used by both state change jobs
    and advertised jobs.
    """

    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        filesystems = kwargs["filesystems"]
        self.invoke_agent(host, "unmount_lustre_filesystems", {"filesystems": filesystems})


class DeleteLustreClientMountStep(Step):
    """
    Marks the client mount as deleted, usually by way of a state
    transition to removed.
    """

    idempotent = True
    database = True

    def run(self, kwargs):
        client_mount = kwargs["client_mount"]
        client_mount.mark_deleted()
        client_mount.save()


class MountLustreClientJob(StateChangeJob):
    """
    Enables the client mount to be transitioned from unmounted -> mounted
    as part of a dependency resolution phase.
    """

    state_transition = StateChangeJob.StateTransition(LustreClientMount, "unmounted", "mounted")
    stateful_object = "lustre_client_mount"
    lustre_client_mount = models.ForeignKey(LustreClientMount)
    state_verb = None

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["mount_lustre_filesystem"]

    def get_confirmation_string(self):
        return MountLustreClientJob.long_description(None)

    def description(self):
        return "Mount %s" % self.lustre_client_mount

    def get_steps(self):
        host = ObjectCache.get_one(ManagedHost, lambda mh: mh.id == self.lustre_client_mount.host_id)
        from chroma_core.models.filesystem import ManagedFilesystem

        filesystem = ObjectCache.get_one(ManagedFilesystem, lambda mf: mf.id == self.lustre_client_mount.filesystem_id)
        args = dict(host=host, filesystems=[(filesystem.mount_path(), self.lustre_client_mount.mountpoint)])
        return [(MountLustreFilesystemsStep, args)]

    def get_deps(self):
        return DependOn(
            ObjectCache.get_one(ManagedHost, lambda mh: mh.id == self.lustre_client_mount.host_id).lnet_configuration,
            "lnet_up",
        )

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class UnmountLustreClientMountJob(StateChangeJob):
    """
    Enables the client mount to be transitioned from mounted -> unmounted
    as part of a dependency resolution phase.
    """

    state_transition = StateChangeJob.StateTransition(LustreClientMount, "mounted", "unmounted")
    stateful_object = "lustre_client_mount"
    lustre_client_mount = models.ForeignKey(LustreClientMount)
    state_verb = None

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unmount_lustre_filesystem"]

    def get_requires_confirmation(self):
        return True

    def get_confirmation_string(self):
        return UnmountLustreClientMountJob.long_description(None)

    def description(self):
        return "Unmount %s" % self.lustre_client_mount

    def get_steps(self):
        host = ObjectCache.get_one(ManagedHost, lambda mh: mh.id == self.lustre_client_mount.host_id)
        from chroma_core.models.filesystem import ManagedFilesystem

        filesystem = ObjectCache.get_one(ManagedFilesystem, lambda mf: mf.id == self.lustre_client_mount.filesystem_id)
        args = dict(host=host, filesystems=[(filesystem.mount_path(), self.lustre_client_mount.mountpoint)])
        return [(UnmountLustreFilesystemsStep, args)]

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class RemoveLustreClientJob(StateChangeJob):
    """
    Enables the client mount to be transitioned from unmounted -> removed
    as part of a dependency resolution phase.
    """

    state_transition = StateChangeJob.StateTransition(LustreClientMount, "unmounted", "removed")
    stateful_object = "lustre_client_mount"
    lustre_client_mount = models.ForeignKey(LustreClientMount)
    state_verb = None

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["remove_lustre_client_mount"]

    def get_requires_confirmation(self):
        return True

    def get_confirmation_string(self):
        return RemoveLustreClientJob.long_description(None)

    def description(self):
        return "Remove %s" % self.lustre_client_mount

    def get_steps(self):
        return [(DeleteLustreClientMountStep, {"client_mount": self.lustre_client_mount})]

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class MountLustreFilesystemsJob(AdvertisedJob):
    """
    Enables all associated client mounts for a given host to be transitioned
    from unmounted -> mounted as the result of a direct user request.

    This job exists so that we can reduce UI clutter by hanging it off
    of a worker node rather than adding new UI just for fiddling with
    a filesystem.
    """

    host = models.ForeignKey(ManagedHost)
    classes = ["ManagedHost"]
    verb = "Mount Filesystem(s)"

    requires_confirmation = True

    display_group = Job.JOB_GROUPS.RARE
    display_order = 120

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["mount_lustre_filesystems"]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    @classmethod
    def can_run(cls, host):
        if not host.is_worker:
            return False

        search = lambda cm: (cm.host == host and cm.state == "unmounted")
        unmounted = ObjectCache.get(LustreClientMount, search)
        return (
            host.state not in ["removed", "undeployed", "unconfigured"]
            and len(unmounted) > 0
            and not AlertState.filter_by_item(host)
            .filter(active=True, alert_type__in=[HostOfflineAlert.__name__, HostContactAlert.__name__])
            .exists()
        )

    def description(self):
        return "Mount associated Lustre filesystem(s) on host %s" % self.host

    def get_steps(self):
        search = lambda cm: (cm.host == self.host and cm.state == "unmounted")
        unmounted = ObjectCache.get(LustreClientMount, search)
        args = dict(host=self.host, filesystems=[(m.filesystem.mount_path(), m.mountpoint) for m in unmounted])
        return [(MountLustreFilesystemsStep, args)]


class UnmountLustreFilesystemsJob(AdvertisedJob):
    """
    Enables all associated client mounts for a given host to be transitioned
    from mounted -> unmounted as the result of a direct user request.

    This job exists so that we can reduce UI clutter by hanging it off
    of a worker node rather than adding new UI just for fiddling with
    a filesystem.
    """

    host = models.ForeignKey(ManagedHost)
    classes = ["ManagedHost"]
    verb = "Unmount Filesystem(s)"

    requires_confirmation = True

    display_group = Job.JOB_GROUPS.RARE
    display_order = 130

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unmount_lustre_filesystems"]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    @classmethod
    def can_run(cls, host):
        if not host.is_worker:
            return False

        search = lambda cm: (cm.host == host and cm.state == "mounted")
        mounted = ObjectCache.get(LustreClientMount, search)
        return (
            host.state not in ["removed", "undeployed", "unconfigured"]
            and len(mounted) > 0
            and not AlertState.filter_by_item(host)
            .filter(active=True, alert_type__in=[HostOfflineAlert.__name__, HostContactAlert.__name__])
            .exists()
        )

    def description(self):
        return "Unmount associated Lustre filesystem(s) on host %s" % self.host

    def get_steps(self):
        search = lambda cm: (cm.host == self.host and cm.state == "mounted")
        mounted = ObjectCache.get(LustreClientMount, search)
        args = dict(host=self.host, filesystems=[(m.filesystem.mount_path(), m.mountpoint) for m in mounted])
        return [(UnmountLustreFilesystemsStep, args)]
