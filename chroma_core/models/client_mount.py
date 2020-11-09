# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models
from django.db.models import CASCADE
from django.contrib.postgres.fields import ArrayField
from chroma_core.models.host import ManagedHost, HostOfflineAlert, HostContactAlert
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.models.jobs import DeletableStatefulObject
from chroma_core.models.jobs import StateChangeJob
from chroma_core.models.alert import AlertState
from chroma_core.models.lnet_configuration import LNetConfiguration
from chroma_core.models.jobs import Job, AdvertisedJob
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_help.help import help_text


def reverse_host_dep(mh):
    return list(
        [
            x
            for x in LustreClientMount.objects.filter(host_id=mh.id)
            if (not mh.immutable_state) and ManagedFilesystem.objects.filter(name=x.filesystem).exists()
        ]
    )


def reverse_lnet_dep(lc):
    return list(
        [
            x
            for x in LustreClientMount.objects.filter(host_id=lc.host.id)
            if ManagedFilesystem.objects.filter(name=x.filesystem, immutable_state=False).exists()
        ]
    )


class LustreClientMount(DeletableStatefulObject):
    host = models.ForeignKey("ManagedHost", help_text="Mount host", related_name="client_mounts", on_delete=CASCADE)
    filesystem = models.CharField(
        max_length=8,
        help_text="Mounted filesystem",
        null=False,
        blank=False,
    )
    mountpoints = ArrayField(models.TextField(), default=list, help_text="Filesystem mountpoints on host")

    states = ["unmounted", "mounted", "removed", "forgotten"]
    initial_state = "unmounted"

    def __str__(self):
        return self.get_label()

    @property
    def active(self):
        return self.state == "mounted"

    def get_label(self):
        return "%s:%s (%s)" % (self.host, self.mountpoints, self.state)

    def get_deps(self, state=None):
        if not state:
            state = self.state

        deps = []
        if state == "mounted":
            # Depend on this mount's host having LNet up. If LNet is stopped
            # on the host, this filesystem will be unmounted first.
            deps.append(DependOn(self.host.lnet_configuration, "lnet_up", fix_state="unmounted"))

        if state != "removed":
            try:
                fs = ManagedFilesystem.objects.get(name=self.filesystem)

                # Depend on the fs being available.
                deps.append(
                    DependOn(
                        fs,
                        "available",
                        acceptable_states=list(set(fs.states) - set(["stopped", "removed"])),
                        fix_state="unmounted",
                    )
                )

                # If the filesystem is removed, the
                # mount should follow.
                deps.append(
                    DependOn(
                        fs,
                        "available",
                        acceptable_states=list(set(fs.states) - set(["removed", "forgotten"])),
                        fix_state="forgotten",
                    )
                )
            except ManagedFilesystem.DoesNotExist:
                pass

            # If the host is removed, the
            # mount should follow.
            deps.append(
                DependOn(
                    self.host,
                    "lnet_up",
                    acceptable_states=list(set(self.host.states) - set(["removed", "forgotten"])),
                    fix_state="removed",
                )
            )

        return DependAll(deps)

    reverse_deps = {
        "ManagedHost": reverse_host_dep,
        "LNetConfiguration": reverse_lnet_dep,
        "ManagedFilesystem": lambda mf: list(LustreClientMount.objects.filter(filesystem=mf.name)),
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
        self.invoke_rust_agent(host, "mount_many", filesystems)


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
        self.invoke_rust_agent(host, "unmount_many", filesystems)


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
    lustre_client_mount = models.ForeignKey(LustreClientMount, on_delete=CASCADE)
    state_verb = None

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["mount_lustre_filesystem"]

    def get_confirmation_string(self):
        return MountLustreClientJob.long_description(None)

    def description(self):
        return "Mount %s" % self.lustre_client_mount

    def get_steps(self):
        from chroma_core.lib.graphql import get_client_mount_source

        host = ManagedHost.objects.filter(id=self.lustre_client_mount.host_id).values("fqdn").first()

        mountspec = get_client_mount_source(fs_name=self.lustre_client_mount.filesystem)

        mountpoint = (
            self.lustre_client_mount.mountpoints[0]
            if self.lustre_client_mount.mountpoints
            else "/mnt/{}".format(self.lustre_client_mount.filesystem)
        )

        args = {
            "host": host.get("fqdn"),
            "filesystems": [{"mountspec": mountspec, "mountpoint": mountpoint, "persist": False}],
        }
        return [(MountLustreFilesystemsStep, args)]

    def get_deps(self):
        return DependOn(LNetConfiguration.objects.get(host_id=self.lustre_client_mount.host_id), "lnet_up")

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
    lustre_client_mount = models.ForeignKey(LustreClientMount, on_delete=CASCADE)
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

    def can_run(self):
        client_mount = self.lustre_client_mount
        return ManagedFilesystem.objects.filter(name=client_mount.filesystem).exists()

    def get_steps(self):
        from chroma_core.lib.graphql import get_client_mount_source

        client_mount = self.lustre_client_mount
        host = ManagedHost.objects.filter(id=client_mount.host_id).values("fqdn").first()
        mount_spec = get_client_mount_source(fs_name=client_mount.filesystem)
        filesystems = [{"mountspec": mount_spec, "mountpoint": x} for x in client_mount.mountpoints]

        args = {"host": host.get("fqdn"), "filesystems": filesystems}
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
    lustre_client_mount = models.ForeignKey(LustreClientMount, on_delete=CASCADE)
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


class ForgetLustreClientJob(StateChangeJob):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    state_transition = StateChangeJob.StateTransition(LustreClientMount, ["unmounted", "mounted"], "forgotten")
    stateful_object = "lustre_client_mount"
    state_verb = "Forget"
    lustre_client_mount = models.ForeignKey(LustreClientMount, on_delete=CASCADE)
    requires_confirmation = True

    @classmethod
    def long_description(cls, stateful_object):
        return "Forget this client mount on the manager. The actual client mount will not be altered."

    def description(self):
        return "Forget client mount {}".format(self.lustre_client_mount)

    def on_success(self):
        super(ForgetLustreClientJob, self).on_success()

        self.lustre_client_mount.mark_deleted()


class MountLustreFilesystemsJob(AdvertisedJob):
    """
    Enables all associated client mounts for a given host to be transitioned
    from unmounted -> mounted as the result of a direct user request.

    This job exists so that we can reduce UI clutter by hanging it off
    of a worker node rather than adding new UI just for fiddling with
    a filesystem.
    """

    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)
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
        if host.immutable_state:
            return False

        cnt = LustreClientMount.objects.filter(state="unmounted", host=host).count()

        return (
            host.state not in ["removed", "undeployed", "unconfigured"]
            and cnt > 0
            and not AlertState.filter_by_item(host)
            .filter(active=True, alert_type__in=[HostOfflineAlert.__name__, HostContactAlert.__name__])
            .exists()
        )

    def description(self):
        return "Mount associated Lustre filesystem(s) on host %s" % self.host

    def get_steps(self):
        from chroma_core.lib.graphql import get_client_mount_source

        unmounted = LustreClientMount.objects.filter(state="unmounted", host=self.host)

        args = {
            "host": self.host.fqdn,
            "filesystems": [
                {
                    "mountspec": get_client_mount_source(fs_name=m.filesystem),
                    "mountpoint": m.mountpoints[0] if m.mountpoints else "/mnt/{}".format(m.filesystem),
                    "persist": False,
                }
                for m in unmounted
            ],
        }

        return [(MountLustreFilesystemsStep, args)]


class UnmountLustreFilesystemsJob(AdvertisedJob):
    """
    Enables all associated client mounts for a given host to be transitioned
    from mounted -> unmounted as the result of a direct user request.

    This job exists so that we can reduce UI clutter by hanging it off
    of a worker node rather than adding new UI just for fiddling with
    a filesystem.
    """

    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)
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
        if host.immutable_state:
            return False

        cnt = LustreClientMount.objects.filter(state="mounted", host=host).count()

        return (
            host.state not in ["removed", "undeployed", "unconfigured"]
            and cnt > 0
            and not AlertState.filter_by_item(host)
            .filter(active=True, alert_type__in=[HostOfflineAlert.__name__, HostContactAlert.__name__])
            .exists()
        )

    def description(self):
        return "Unmount associated Lustre filesystem(s) on host %s" % self.host

    def get_steps(self):
        from chroma_core.lib.graphql import get_client_mount_source

        mounted = LustreClientMount.objects.filter(state="mounted", host=self.host)

        filesystems = []

        for m in mounted:
            mount_spec = get_client_mount_source(fs_name=m.filesystem)

            filesystems.extend([{"mountspec": mount_spec, "mountpoint": x} for x in m.mountpoints])

        args = {
            "host": self.host.fqdn,
            "filesystems": filesystems,
        }

        return [(UnmountLustreFilesystemsStep, args)]
