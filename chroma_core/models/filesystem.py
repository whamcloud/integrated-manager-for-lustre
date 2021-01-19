# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import functools
import operator
from django.db import models
from django.db.models import CASCADE
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_core.models.target import FilesystemMember
from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedTarget, ManagedHost
from chroma_core.models.jobs import StatefulObject, StateChangeJob, Job, AdvertisedJob
from chroma_core.models.utils import DeletableDowncastableMetaclass
from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.util import target_label_split
from django.db.models import Q
from chroma_help.help import help_text


HSM_CONTROL_KEY = "mdt.hsm_control"
HSM_CONTROL_PARAMS = {
    "disabled": {"verb": "Disable", "long_description": help_text["hsm_control_disabled"]},
    "enabled": {"verb": "Enable", "long_description": help_text["hsm_control_enabled"]},
    "shutdown": {"verb": "Shutdown", "long_description": help_text["hsm_control_shutdown"]},
}


### Given a filesystem id or name, this function will return the id of the filesystem associated
### with the identifier or None if it cannot be found.
def get_fs_id_from_identifier(fs_identifier):
    if fs_identifier is None:
        return None

    try:
        fs_id = int(str(fs_identifier), 10)
        return ManagedFilesystem.objects.filter(id=fs_id).values_list("id", flat=True).first()
    except ValueError:
        return ManagedFilesystem.objects.filter(name=fs_identifier).values_list("id", flat=True).first()


class ManagedFilesystem(StatefulObject):
    __metaclass__ = DeletableDowncastableMetaclass

    name = models.CharField(
        max_length=8,
        help_text="Lustre filesystem name, up to 8\
            characters",
    )
    mgs = models.ForeignKey("ManagedMgs", on_delete=CASCADE)

    states = ["unavailable", "stopped", "available", "removed", "forgotten"]
    initial_state = "unavailable"

    mdt_next_index = models.IntegerField(default=0)
    ost_next_index = models.IntegerField(default=0)

    def get_label(self):
        return self.name

    def get_available_states(self, begin_state):
        if self.immutable_state:
            return ["forgotten"]
        else:
            available_states = super(ManagedFilesystem, self).get_available_states(begin_state)
            excluded_states = []

            # Exclude 'stopped' if we are in 'unavailable' and everything is stopped
            target_states = set([t.state for t in self.get_filesystem_targets()])
            if begin_state == "unavailable" and not "mounted" in target_states:
                excluded_states.append("stopped")

            ticket = self.get_ticket()
            if ticket:
                excluded_states.append("removed")

            available_states = list(set(available_states) - set(excluded_states))

            return available_states

    class Meta:
        app_label = "chroma_core"
        unique_together = ("name", "mgs")
        ordering = ["id"]

    def get_ticket(self):
        from chroma_core.models import FilesystemTicket

        tl = FilesystemTicket.objects.filter(filesystem=self)
        return list(tl)[0].ticket if len(list(tl)) > 0 else None

    def get_targets(self):
        return ManagedTarget.objects.filter(
            (Q(managedmdt__filesystem=self) | Q(managedost__filesystem=self)) | Q(id=self.mgs_id)
        )

    def get_filesystem_targets(self):
        return ManagedTarget.objects.filter((Q(managedmdt__filesystem=self) | Q(managedost__filesystem=self)))

    def get_servers(self):
        from chroma_core.lib.graphql import get_targets

        xs = [x["host_ids"] for x in get_targets(fsname=self.name)]

        ids = set(functools.reduce(operator.iconcat, xs, []))

        return ManagedHost.objects.filter(id__in=ids)

    def get_server_groups(self):
        """Return: Array(Array(ManagedHost)) """
        from chroma_core.lib.graphql import graphql_query

        query = '{{ getFsClusterHosts(fsName: "{}") }}'.format(self.name)

        return graphql_query(query)["getFsClusterHosts"]

    def get_pools(self):
        return OstPool.objects.filter(filesystem=self)

    def __str__(self):
        return self.name

    def get_deps(self, state=None):
        if not state:
            state = self.state

        deps = []

        mgs = ObjectCache.get_one(ManagedTarget, lambda t: t.id == self.mgs_id, fill_on_miss=True)

        remove_state = "forgotten" if self.immutable_state else "removed"

        if state not in ["removed", "forgotten"]:
            deps.append(
                DependOn(
                    mgs, "unmounted", acceptable_states=mgs.not_states(["removed", "forgotten"]), fix_state=remove_state
                )
            )

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
        "ManagedTarget": lambda mt: ManagedFilesystem.filter_by_target(mt),
        "FilesystemTicket": lambda fst: [fst.ticket],
    }


class StartStoppedFilesystemJob(StateChangeJob):
    state_verb = "Start"
    state_transition = StateChangeJob.StateTransition(ManagedFilesystem, "stopped", "available")
    filesystem = models.ForeignKey("ManagedFilesystem", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10
    stateful_object = "filesystem"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return []

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_file_system"]

    def description(self):
        return "Start file system %s" % self.filesystem.name

    def get_deps(self):
        ticket = self.filesystem.get_ticket()
        if ticket:
            return DependAll(DependOn(ticket, "granted", fix_state="unavailable"))

        deps = []
        for t in ObjectCache.get_targets_by_filesystem(self.filesystem_id):
            # Report filesystem available if MDTs other than 0 are unmounted
            (_, label, index) = target_label_split(t.get_label())
            if label == "MDT" and index != 0:
                continue
            deps.append(DependOn(t, "mounted", fix_state="unavailable"))
        return DependAll(deps)


class StartUnavailableFilesystemJob(StateChangeJob):
    state_verb = "Start"
    state_transition = StateChangeJob.StateTransition(ManagedFilesystem, "unavailable", "available")
    filesystem = models.ForeignKey("ManagedFilesystem", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 20
    stateful_object = "filesystem"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return []

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_file_system"]

    def description(self):
        return "Start filesystem %s" % self.filesystem.name

    def get_deps(self):
        ticket = self.filesystem.get_ticket()
        if ticket:
            return DependAll([DependOn(ticket, "granted", fix_state="unavailable")])

        deps = []

        for t in ObjectCache.get_targets_by_filesystem(self.filesystem_id):
            # Report filesystem available if MDTs other than 0 are unmounted
            (_, label, index) = target_label_split(t.get_label())
            if label == "MDT" and index != 0:
                continue
            deps.append(DependOn(t, "mounted", fix_state="unavailable"))
        return DependAll(deps)


class StopUnavailableFilesystemJob(StateChangeJob):
    state_verb = "Stop"
    state_transition = StateChangeJob.StateTransition(ManagedFilesystem, "unavailable", "stopped")
    filesystem = models.ForeignKey("ManagedFilesystem", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 30
    stateful_object = "filesystem"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return []

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["stop_file_system"]

    def description(self):
        return "Stop file system %s" % self.filesystem.name

    def get_deps(self):
        ticket = self.filesystem.get_ticket()
        if ticket:
            return DependAll([DependOn(ticket, "revoked", fix_state="unavailable")])

        deps = []
        targets = ObjectCache.get_targets_by_filesystem(self.filesystem_id)
        targets = [t for t in targets if not issubclass(t.downcast_class, ManagedMgs)]
        for t in targets:
            deps.append(DependOn(t, "unmounted", acceptable_states=t.not_state("mounted"), fix_state="unavailable"))
        return DependAll(deps)


class MakeAvailableFilesystemUnavailable(StateChangeJob):
    """This Job has no steps, so does nothing other then change the state.

    Although the get_available_job code will find this Job as an option when the FS
    is in state 'available', because state_verb is None JobScheduler:_add_verbs will strip it out.

    TODO:  RECOMMEND A REVIEW BEFORE RUNNING THIS JOB TO DETERMINE WHAT THE UNAVAILABLE STATE MEANS, OTHER THAN JUST THE
    STARTING STATE.
    """

    state_verb = None
    state_transition = StateChangeJob.StateTransition(ManagedFilesystem, "available", "unavailable")
    filesystem = models.ForeignKey("ManagedFilesystem", on_delete=CASCADE)
    stateful_object = "filesystem"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return []

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["make_file_system_unavailable"]

    def description(self):
        return "Make file system %s unavailable" % self.filesystem.name


class ForgetFilesystemJob(StateChangeJob):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    display_group = Job.JOB_GROUPS.RARE
    display_order = 40

    state_transition = StateChangeJob.StateTransition(
        ManagedFilesystem, ["unavailable", "stopped", "available"], "forgotten"
    )
    stateful_object = "filesystem"
    state_verb = "Forget"
    filesystem = models.ForeignKey(ManagedFilesystem, on_delete=CASCADE)
    requires_confirmation = True

    @classmethod
    def long_description(cls, stateful_object):
        return "Forget this filesystem on the manager. The actual filesystem will not be altered."

    def description(self):
        return "Forget filesystem {}".format(self.filesystem.name)

    def on_success(self):
        super(ForgetFilesystemJob, self).on_success()

        assert ManagedMdt.objects.filter(filesystem=self.filesystem).count() == 0
        assert ManagedOst.objects.filter(filesystem=self.filesystem).count() == 0
        self.filesystem.mark_deleted()

    def get_deps(self):
        deps = []
        ticket = self.filesystem.get_ticket()
        if ticket:
            deps.append(DependOn(ticket, "forgotten", fix_state=ticket.state))

        for t in self.filesystem.get_filesystem_targets():
            deps.append(DependOn(t, "forgotten"))

        return DependAll(deps)


class OstPool(models.Model):
    __metaclass__ = DeletableDowncastableMetaclass

    name = models.CharField(max_length=15, help_text="OST Pool name, up to 15 characters")

    filesystem = models.ForeignKey("ManagedFilesystem", on_delete=CASCADE)

    osts = models.ManyToManyField(ManagedOst, help_text="OST list in this Pool")

    class Meta:
        app_label = "chroma_core"
        unique_together = ("name", "filesystem")
        ordering = ["id"]


class CreateOstPoolJob(AdvertisedJob):
    pool = models.ForeignKey("OstPool", on_delete=CASCADE)

    requires_confirmation = False

    classes = ["OstPool"]

    verb = "Create"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return "Create OST Pool"

    @classmethod
    def can_run(self, instance):
        mgs = instance.filesystem.mgs
        mdt0 = instance.filesystem.name + "-MDT0000"
        mds0 = next(t.active_host for t in instance.filesystem.get_targets() if t.name == mdt0)
        return mgs is not None and mgs.active_host is not None and mds0 is not None

    @classmethod
    def get_args(cls, pool):
        return {"pool_id": pool.id}

    def description(self):
        return "Create OST Pool"

    def get_steps(self):
        mdt0 = self.pool.filesystem.name + "-MDT0000"
        return [
            (
                CreateOstPoolStep,
                {
                    "pool": self.pool.name,
                    "filesystem": self.pool.filesystem.name,
                    "mgs": self.pool.filesystem.mgs.active_host.fqdn,
                },
            ),
            (
                WaitOstPoolStep,
                {
                    "pool": self.pool.name,
                    "filesystem": self.pool.filesystem.name,
                    "mds": next(t.active_host.fqdn for t in self.pool.filesystem.get_targets() if t.name == mdt0),
                },
            ),
        ]


class CreateOstPoolStep(Step):
    def run(self, kwargs):
        pool_name = kwargs["pool"]
        fs_name = kwargs["filesystem"]
        host = kwargs["mgs"]

        self.invoke_rust_agent_expect_result(host, "ostpool_create", {"filesystem": fs_name, "name": pool_name})


class WaitOstPoolStep(Step):
    def run(self, kwargs):
        pool_name = kwargs["pool"]
        fs_name = kwargs["filesystem"]
        host = kwargs["mds"]

        self.invoke_rust_agent_expect_result(host, "ostpool_wait", {"filesystem": fs_name, "name": pool_name})


class DestroyOstPoolJob(AdvertisedJob):
    pool = models.ForeignKey("OstPool", on_delete=CASCADE)

    requires_confirmation = True

    classes = ["OstPool"]

    verb = "Destroy"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return "Destroy OST Pool"

    @classmethod
    def can_run(self, instance):
        mgs = instance.filesystem.mgs
        return mgs is not None and mgs.active_host is not None

    @classmethod
    def get_args(cls, pool):
        return {"pool_id": pool.id}

    def description(self):
        return "Destroy OST Pool"

    def get_steps(self):
        return [
            (
                DestroyOstPoolStep,
                {
                    "pool": self.pool.name,
                    "filesystem": self.pool.filesystem.name,
                    "mgs": self.pool.filesystem.mgs.active_host.fqdn,
                },
            )
        ]

    def on_success(self):
        super(DestroyOstPoolJob, self).on_success()

        self.pool.mark_deleted()
        self.pool.save()


class DestroyOstPoolStep(Step):
    def run(self, kwargs):
        pool_name = kwargs["pool"]
        fs_name = kwargs["filesystem"]
        host = kwargs["mgs"]

        self.invoke_rust_agent_expect_result(host, "ostpool_destroy", {"filesystem": fs_name, "name": pool_name})


class AddOstPoolJob(Job):
    """
    Add an OST from a Pool
    """

    pool = models.ForeignKey("OstPool", null=False, on_delete=CASCADE)
    ost = models.ForeignKey("ManagedOst", null=False, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def can_run(self, instance):
        mgs = instance.filesystem.mgs
        return mgs is not None and mgs.active_host is not None

    @classmethod
    def long_description(self):
        return "Add OST to OST Pool"

    def description(self):
        return "Add OST to OST Pool"

    def get_steps(self):
        return [
            (
                AddOstPoolStep,
                {
                    "pool": self.pool.name,
                    "filesystem": self.pool.filesystem.name,
                    "mgs": self.pool.filesystem.mgs.active_host.fqdn,
                    "ost": self.ost.get_label(),
                },
            )
        ]

    def on_success(self):
        super(AddOstPoolJob, self).on_success()
        self.pool.osts.add(self.ost)


class AddOstPoolStep(Step):
    def run(self, kwargs):
        pool_name = kwargs["pool"]
        fs_name = kwargs["filesystem"]
        host = kwargs["mgs"]
        ost_label = kwargs["ost"]

        self.invoke_rust_agent_expect_result(
            host, "ostpool_add", {"filesystem": fs_name, "name": pool_name, "ost": ost_label}
        )


class RemoveOstPoolJob(Job):
    """
    Remove an OST from a Pool
    """

    pool = models.ForeignKey("OstPool", null=False, on_delete=CASCADE)
    ost = models.ForeignKey("ManagedOst", null=False, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def can_run(self, instance):
        mgs = instance.filesystem.mgs
        return mgs is not None and mgs.active_host is not None

    @classmethod
    def long_description(self):
        return "Remove OST from OST Pool"

    def description(self):
        return "Remove OST from OST Pool"

    def get_steps(self):
        return [
            (
                RemoveOstPoolStep,
                {
                    "pool": self.pool.name,
                    "filesystem": self.pool.filesystem.name,
                    "mgs": self.pool.filesystem.mgs.active_host.fqdn,
                    "ost": self.ost.get_label(),
                },
            )
        ]

    def on_success(self):
        super(RemoveOstPoolJob, self).on_success()
        self.pool.osts.remove(self.ost)


class RemoveOstPoolStep(Step):
    def run(self, kwargs):
        pool_name = kwargs["pool"]
        fs_name = kwargs["filesystem"]
        host = kwargs["mgs"]
        ost_label = kwargs["ost"]

        self.invoke_rust_agent_expect_result(
            host, "ostpool_remove", {"filesystem": fs_name, "name": pool_name, "ost": ost_label}
        )
