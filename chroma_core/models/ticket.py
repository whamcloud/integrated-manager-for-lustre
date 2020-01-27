# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from django.db import models
from django.db.models import CASCADE, Q
from chroma_core.lib.job import DependOn, DependAll, Step, job_log
from chroma_core.models import DeletableDowncastableMetaclass, ManagedFilesystem
from chroma_core.models import StatefulObject, StateChangeJob, StateLock, Job, AdvertisedJob
from chroma_help.help import help_text


class Ticket(StatefulObject):
    __metaclass__ = DeletableDowncastableMetaclass

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    states = ["revoked", "granted", "forgotten"]
    initial_state = "revoked"

    ha_label = models.CharField(
        max_length=64, null=True, blank=True, help_text="Label used for HA layer; human readable but unique"
    )

    name = models.CharField(max_length=64, null=False, blank=False, help_text="Name of ticket",)

    resource_controlled = models.BooleanField(
        default=True, help_text="Ticket is controlled by a resources named in `ha_label`"
    )


class MasterTicket(Ticket):
    """
    Ticket that controls all other filesystem tickets and the MGS
    """

    mgs = models.ForeignKey("ManagedMgs", null=False, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_host(self):
        return self.mgs.best_available_host()


class FilesystemTicket(Ticket):
    """
    Ticket that controls a named filesystem

    """

    filesystem = models.ForeignKey("ManagedFilesystem", null=False, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_deps(self, state=None):
        deps = []
        mt = MasterTicket.objects.filter(mgs=self.filesystem.mgs)
        if state == "granted":
            deps.append(DependOn(mt, "granted"))
        return DependAll(deps)

    def get_host(self):
        return self.filesystem.mgs.best_available_host()


class GrantRevokedTicketJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Ticket, "revoked", "granted")
    stateful_object = "ticket"
    state_verb = "Grant"

    ticket = models.ForeignKey("Ticket", on_delete=CASCADE)

    def get_steps(self):
        steps = []
        if self.ticket.resource_controlled:
            steps.append((StartResourceStep, {"host": self.ticket.get_host(), "ha_label": self.ticket.ha_label}))
        else:
            raise RuntimeError("Ticket `%s' is not resource controlled" % self.ticket.name)

        return steps


class RevokeGrantedTicketJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Ticket, "granted", "revoked")
    stateful_object = "ticket"
    state_verb = "Revoke"

    ticket = models.ForeignKey("Ticket", on_delete=CASCADE)

    def get_steps(self):
        steps = []

        if self.ticket.resource_controlled:
            steps.append((StartResourceStep, {"host": self.ticket.get_host(), "ha_label": self.ticket.ha_label}))
        else:
            raise RuntimeError("Ticket `%s' is not resource controlled" % self.ticket.name)

        return steps


class StartResourceStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.inoke_agent(kwargs["host"], "start_target", {"ha_label", kwargs["ha_label"]})


class StopResourceStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.inoke_agent(kwargs["host"], "stop_target", {"ha_label", kwargs["ha_label"]})
