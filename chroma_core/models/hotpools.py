# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import logging
import os

from django.db import models
from django.db.models import CASCADE, Q
from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.job import DependOn, DependAll, Step, job_log
from chroma_core.models.jobs import StatefulObject, StateChangeJob, Job
from chroma_core.models.utils import (
    DeletableMetaclass,
    StartResourceStep,
    StopResourceStep,
    MountStep,
    UnmountStep,
    CreateSystemdResourceStep,
    RemoveResourceStep,
)
from chroma_core.models import (
    ManagedFilesystem,
    ManagedMdt,
    OstPool,
    Task,
)
from chroma_help.help import help_text

############################################################
# Hotpools
#
# Assumptions:
# * components will be controlled via pacemaker
# * is_single_resource implies single resources is cloned client mount across servers


class HotpoolConfiguration(StatefulObject):
    __metaclass__ = DeletableMetaclass

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    states = ["unconfigured", "stopped", "started", "removed"]
    initial_state = "unconfigured"

    filesystem = models.ForeignKey("ManagedFilesystem", null=False, on_delete=CASCADE)
    ha_label = models.CharField(
        max_length=64,
        null=True,
        blank=False,
        help_text="Set if there is a single resource that will controll entire hotpools configuration",
    )
    version = models.PositiveSmallIntegerField(default=2, null=False)

    def get_label(self):
        return "Hotpool Configuration"

    def is_single_resource(self):
        return self.ha_label is not None

    def get_components(self):
        # self.version == 2:
        component_types = [Lamigo, Lpurge]

        components = []
        for ctype in component_types:
            components.extend([x for x in Lamigo.objects.filter(configuration__hotpool=self)])

        return components

    def get_deps(self, state=None):
        if not state:
            state = self.state

        deps = []
        if state != "unconfigured":
            # Depend on the filesystem being available.
            deps.append(DependOn(self.filesystem, "available"))

        return DependAll(deps)


class ConfigureHotpoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(HotpoolConfiguration, "unconfigured", "stopped")
    stateful_object = "hotpool_configuration"
    hotpool_configuration = models.ForeignKey(HotpoolConfiguration, on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Configure Hotpool"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        fs = self.hotpool_configuration.filesystem
        mp = "/lustre/" + fs.name + "/client"

        if self.hotpool_configuration.is_single_resource():
            # create cloned client mount
            for host in fs.get_servers():
                # c.f. iml-wire-types::client::Mount
                # Mount.persist equates to automount
                steps.append(
                    (MountStep, {"host": host.fqdn, "auto": False, "spec": filesystem.mount_path(), "point": mp})
                )

            for host in (l[0] for l in fs.get_server_groups()):
                steps.append((CreateClonedClientStep, {"host": host.fqdn, "mountpoint": mp}))

        return steps

    def get_deps(self):
        deps = []

        for comp in self.hotpool_configuration.get_components():
            deps.append(DependOn(comp, "configured", fix_state="unconfigured"))

        return DependAll(deps)


class CreateClonedClientStep(Step):
    """
    Create a cloned Client mount on server
    """

    def run(self, kwargs):
        host = kwargs["host"]
        mp = kwargs["mountpoint"]

        self.invoke_rust_agent_expect_result(host, "create_cloned_mount", mp)


class StartHotpoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(HotpoolConfiguration, "stopped", "started")
    stateful_object = "hotpool_configuration"
    hotpool_configuration = models.ForeignKey(HotpoolConfiguration, on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Start Hotpool"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_hotpool_long"]

    def description(self):
        return help_text["start_hotpool_long"]

    def get_deps(self):
        deps = []

        fs = self.hotpool_configuration.filesystem
        deps.append(DependOn(fs, "available", fix_state="stopped"))

        if not self.hotpool_configuration.is_single_resource():
            for comp in self.hotpool_configuration.get_components():
                deps.append(DependOn(comp, "started", fix_state="stopped"))

        return DependAll(deps)

    def get_steps(self):
        steps = []

        if self.hotpool_configuration.is_single_resource():
            for host in (l[0] for l in fs.get_server_groups()):
                steps.append((StartResourceStep, {"host": host.fqdn, "ha_label": self.hotpool_configuration.ha_label}))

            # @@ wait for component starts?

        return steps


class StopHotpoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(HotpoolConfiguration, "started", "stopped")
    stateful_object = "hotpool_configuration"
    hotpool_configuration = models.ForeignKey(HotpoolConfiguration, on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Start Hotpool"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["stop_hotpool_long"]

    def description(self):
        return help_text["stop_hotpool_long"]

    def get_steps(self):
        steps = []
        if self.hotpool_configuration.is_single_resource():
            for host in (l[0] for l in fs.get_server_groups()):
                steps.append((StopResourceStep, {"host": host.fqdn, "ha_label": self.hotpool_configuration.ha_label}))

        return steps


class RemoveHotpoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(HotpoolConfiguration, "stopped", "removed")
    stateful_object = "hotpool_configuration"
    hotpool_configuration = models.ForeignKey(HotpoolConfiguration, on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Start Hotpool"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["stop_hotpool_long"]

    def description(self):
        return help_text["stop_hotpool_long"]

    def get_deps(self):
        deps = []

        for comp in self.hotpool_configuration.get_components():
            deps.append(DependOn(comp, "removed", fix_state="stopped"))

        return deps

    def get_steps(self):
        steps = []
        if self.hotpool_configuration.is_single_resource():
            fs = self.hotpool_configuration.filesystem
            mp = "/lustre/" + fs.name + "/client"
            for host in (l[0] for l in fs.get_server_groups()):
                steps.append((RemoveClonedClientMountStep, {"host": host.fqdn, "mountpoint": mp}))

        return steps

    def on_success(self):
        self.hotpool_configuration.mark_deleted()
        self.hotpool_configuration.save()


############################################################
# LAmigo
#


class LamigoConfiguration(models.Model):
    """
    Shared configuration for all lamigo instances for a given hotpool configutation
    """

    __metaclass__ = DeletableMetaclass

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    hotpool = models.ForeignKey("HotpoolConfiguration", null=False, on_delete=CASCADE)
    hot = models.ForeignKey("OstPool", related_name="hot", null=False, on_delete=CASCADE)
    cold = models.ForeignKey("OstPool", related_name="cold", null=False, on_delete=CASCADE)

    extend = models.ForeignKey("Task", related_name="extend", null=True, on_delete=CASCADE)
    resync = models.ForeignKey("Task", related_name="resync", null=True, on_delete=CASCADE)

    minage = models.IntegerField(help_text="Seconds to wait after close to sync to cold pool", null=False)

    def lamigo_config(self, mdt, user):
        # C.F. iml-agent::action_plugins::lamigo::Config
        config = {
            "mdt": mdt.index,
            "fs": self.hotpool.filesystem.name,
            "user": user,
            "min_age": self.minage,
            "mailbox_extend": self.extend_task.name,
            "mailbox_resync": self.resync_task.name,
            "hot_pool": self.hot.name,
            "cold_pool": self.cold.name,
        }
        return config


class Lamigo(StatefulObject):
    """
    lamigo instance for a given MDT
    """

    states = ["unconfigured", "stopped", "started", "removed"]
    initial_state = "unconfigured"

    __metaclass__ = DeletableMetaclass

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    configuration = models.ForeignKey("LamigoConfiguration", null=False, on_delete=CASCADE)
    mdt = models.ForeignKey("ManagedMdt", null=False, on_delete=CASCADE)
    changelog_user = models.CharField(max_length=8, null=True, help_text="Name of changelog user for MDT")

    def lamigo_config(self):
        assert self.changelog_user is not None
        return self.configuration.lamigo_config(self.mdt, self.changelog_user)

    @property
    def unit_name(self):
        return "lamigo@" + self.mdt.name + ".service"

    @property
    def ha_label(self):
        return "systemd:" + self.unit_name

    def get_deps(self, state=None):
        if not state:
            state = self.state

        deps = []
        if state == "started":

            # Depend on the filesystem being available.
            deps.append(DependOn(self.filesystem, "available", fix_state="stopped"))

            # move to the removed state if the filesystem is removed.
            deps.append(
                DependOn(
                    self.filesystem,
                    "available",
                    acceptable_states=list(set(self.filesystem.states) - set(["removed", "forgotten"])),
                    fix_state="removed",
                )
            )


class ConfigureLamigoJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lamigo, "unconfigured", "stopped")
    stateful_object = "lamigo"
    lamigo = models.ForeignKey("Lamigo", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Configure Lamigo"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        fs = self.lamigo.configuration.filesystem

        if not self.lamigo.configuration.changelog_user:
            steps.append(
                (
                    CreateChangelogUserStep,
                    {
                        "host": self.lamgo.mdt.active_host().fqdn,
                        "ha_label": self.lamigo.ha_label,
                        "unit": self.lamigo.unit_name,
                        "monitor": 30,
                    },
                )
            )

        for host in self.lamgo.mdt.managedtargetmount_set.all():
            steps.append((ConfigureLamigoStep, {"host": host.fqdn, "lamigo_id": self.lamigo.id}))

        host = self.lamigo.mdt.active_host()
        after = [self.lamigo.mdt.ha_label]
        if self.lamigo.configuration.hotpool.is_single_resource():
            after.append(self.lamigo.configuration.hotpool.ha_label)
        steps.append(
            (
                CreateSystemdResourceStep,
                {
                    "host": host.fqdn,
                    "unit": self.lamigo.unit,
                    "monitor": "30s",
                    "start": "15m",
                    "after": after,
                    "with": [self.lamigo.mdt.ha_label],
                },
            )
        )

        return steps


class CreateChangelogUserStep(Step):
    idempotent = True

    def run(self, kwargs):
        lamigo = Lamigo.objects.get(id=kwargs["lamigo_id"])
        host = kwargs["host"]
        # @@ ideally this should lock lamigo object
        # with lamigo._lock:
        if not lamigo.changelog_user:
            lamigo.changelog_user = self.invoke_rust_agent_expect_result(
                host, "lctl", ["--device", lamigo.mdt.name, "changelog_register", "-n"]
            )
            lamigo.save()


class ConfigureLamigoStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        lamigo = Lamigo.objects.get(id=kwargs["lamigo_id"])

        self.invoke_rust_agent_expect_result(host, "config_lamigo", lamigo.lamigo_config())


class StartLamigoJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lamigo, "stopped", "started")
    stateful_object = "lamigo"
    lamigo = models.ForeignKey("Lamigo", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Start Lamigo"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        if not lamigo.configuration.hotpool.is_single_resource():
            host = self.lamigo.mdt.active_host()
            steps.append((StartResourceStep, {"host": host.fqdn, "ha_label": self.lamigo.ha_label}))

        return steps


class StopLamigoJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lamigo, "started", "stopped")
    stateful_object = "lamigo"
    lamigo = models.ForeignKey("Lamigo", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Stop Lamigo"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        host = self.lamigo.mdt.active_host()
        steps.append((StopResourceStep, {"host": host.fqdn, "ha_label": self.lamigo.ha_label}))

        return steps


class RemoveLamigoJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lamigo, "stopped", "removed")
    stateful_object = "lamigo"
    lamigo = models.ForeignKey("Lamigo", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Remove Lamigo"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        host = self.lamigo.mdt.active_host()
        steps.append((UnconfigureResourceStep, {"host": host.fqdn, "ha_label": self.lamigo.ha_label}))

        return steps

    def on_success(self):
        self.lamigo.mark_deleted()
        self.lamigo.save()


############################################################
# LPurge
#


class LpurgeConfiguration(models.Model):
    """
    Shared configuration for all lpurge instances for a given hotpool configutation
    """

    __metaclass__ = DeletableMetaclass

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    hotpool = models.ForeignKey("HotpoolConfiguration", null=False, on_delete=CASCADE)
    cold = models.ForeignKey("OstPool", null=False, on_delete=CASCADE)

    purge = models.ForeignKey("Task", null=True, on_delete=CASCADE)

    freehi = models.PositiveSmallIntegerField(help_text="Percent of free space which causes purge to stop", null=False)
    freelo = models.PositiveSmallIntegerField(help_text="Percent of free space which causes purge to start", null=False)

    def lpurge_config(self, ost):
        # C.F. iml-agent::action_plugins::lpurge::Config
        config = {
            "ost": ost.index,
            "fs": self.filesystem.name,
            "mailbox": self.purge.name,
            "pool": self.cold.name,
            "freehi": self.freehi,
            "freelo": self.freelo,
        }
        return config


class Lpurge(StatefulObject):
    """
    lpurge instance for a given OST
    """

    states = ["unconfigured", "stopped", "started", "removed"]
    initial_state = "unconfigured"

    __metaclass__ = DeletableMetaclass

    configuration = models.ForeignKey("LpurgeConfiguration", null=False, on_delete=CASCADE)
    ost = models.ForeignKey("ManagedOst", null=False, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def lpurge_config(self):
        return self.configuration.lpurge_config(self.ost)

    @property
    def unit_name(self):
        return "lpurge@" + self.mdt.name + ".service"

    @property
    def ha_label(self):
        return "systemd:" + self.unit_name

    def get_deps(self, state=None):
        if not state:
            state = self.state

        deps = []
        if state == "started":
            # Depend on the filesystem being available.
            deps.append(DependOn(self.filesystem, "available", fix_state="stopped"))

            # move to the removed state if the filesystem is removed.
            deps.append(
                DependOn(
                    self.filesystem,
                    "available",
                    acceptable_states=list(set(self.filesystem.states) - set(["removed", "forgotten"])),
                    fix_state="removed",
                )
            )


class ConfigureLpurgeJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lpurge, "unconfigured", "stopped")
    stateful_object = "lpurge"
    lpurge = models.ForeignKey("Lpurge", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Configure Lpurge"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        fs = self.lpurge.configuration.filesystem

        for host in self.lpurge.ost.managedtargetmount_set.all():
            steps.append((ConfigureLpurgeStep, {"host": host.fqdn, "lpurge_id": self.lpurge.id}))

        host = self.lpurge.ost.active_host()
        after = [self.lpurge.ost.ha_label]
        if self.lpurge.configuration.hotpool.is_single_resource():
            after.append(self.lpurge.configuration.hotpool.ha_label)
        steps.append(
            (
                CreateSystemdResourceStep,
                {
                    "host": host.fqdn,
                    "unit": self.lpurge.unit,
                    "monitor": "30s",
                    "after": after,
                    "with": [self.lpurge.ost.ha_label],
                },
            )
        )

        return steps


class ConfigureLpurgeStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        lpurge = Lpurge.objects.get(id=kwargs["lpurge_id"])

        self.invoke_rust_agent_expect_result(host, "config_lpurge", lpurge.lpurge_config())


class StartLpurgeJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lpurge, "stopped", "started")
    stateful_object = "lpurge"
    lpurge = models.ForeignKey("Lpurge", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    state_verb = "Start Lpurge"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        if not lpurge.configuration.hotpool.is_single_resource():
            host = self.lpurge.ost.active_host()
            steps.append((StartResourceStep, {"host": host.fqdn, "ha_label": self.lpurge.ha_label}))

        return steps


class StopLpurgeJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lpurge, "started", "stopped")
    stateful_object = "lpurge"
    lpurge = models.ForeignKey("Lpurge", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Stop Lpurge"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        host = self.lpurge.ost.active_host()
        steps.append((StopResourceStep, {"host": host.fqdn, "ha_label": self.lpurge.ha_label}))

        return steps


class RemoveLpurgeJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Lpurge, "stopped", "removed")
    stateful_object = "lpurge"
    lpurge = models.ForeignKey("Lpurge", on_delete=CASCADE)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Remove Lpurge"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_hotpool_long"]

    def description(self):
        return help_text["configure_hotpool_long"]

    def get_steps(self):
        steps = []

        host = self.lpurge.ost.active_host()
        steps.append((UnconfigureResourceStep, {"host": host.fqdn, "ha_label": self.lpurge.ha_label}))

        return steps

    def on_success(self):
        self.lpurge.mark_deleted()
        self.lpurge.save()
