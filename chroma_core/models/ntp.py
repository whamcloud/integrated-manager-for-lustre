# -*- coding: utf-8 -*-
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import socket

from django.db import models
from django.db.models import CASCADE
from chroma_core.models import DeletableStatefulObject
from chroma_core.models import StateChangeJob
from chroma_core.models import Job
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_help.help import help_text

import settings


class NTPConfiguration(DeletableStatefulObject):
    states = ["unconfigured", "configured"]
    initial_state = "unconfigured"

    host = models.OneToOneField("ManagedHost", related_name="_ntp_configuration", on_delete=CASCADE)

    def __str__(self):
        return "%s NTP configuration" % self.host

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_label(self):
        return "ntp configuration"

    reverse_deps = {"ManagedHost": lambda mh: NTPConfiguration.objects.filter(host_id=mh.id)}


class ConfigureNTPStep(Step):
    idempotent = True

    def run(self, kwargs):
        if settings.NTP_SERVER_HOSTNAME:
            ntp_server = settings.NTP_SERVER_HOSTNAME
        else:
            ntp_server = socket.getfqdn()

        return self.invoke_rust_agent_expect_result(kwargs["fqdn"], "configure_ntp", ntp_server)


class StopChronyStep(Step):
    idempotent = True

    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(kwargs["fqdn"], "stop_unit", "chronyd.service")


class DisableChronyStep(Step):
    idempotent = True

    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(kwargs["fqdn"], "disable_unit", "chronyd.service")


class EnableNtpStep(Step):
    idempotent = True

    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(kwargs["fqdn"], "enable_unit", "ntpd.service")


class RestartNtpStep(Step):
    idempotent = True

    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(kwargs["fqdn"], "restart_unit", "ntpd.service")


class ConfigureNTPJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(NTPConfiguration, "unconfigured", "configured")
    stateful_object = "ntp_configuration"
    ntp_configuration = models.ForeignKey(NTPConfiguration, on_delete=CASCADE)
    state_verb = "Start Ntp"

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_ntp"]

    def description(self):
        return "Configure NTP on {}".format(self.ntp_configuration.host)

    def get_steps(self):
        fqdn = self.ntp_configuration.host.fqdn

        return [
            (ConfigureNTPStep, {"fqdn": fqdn}),
            (StopChronyStep, {"fqdn": fqdn}),
            (DisableChronyStep, {"fqdn": fqdn}),
            (EnableNtpStep, {"fqdn": fqdn}),
            (RestartNtpStep, {"fqdn": fqdn}),
        ]

    def get_deps(self):
        """
        Before ntp operations are possible some dependencies are need, basically the host must have had its packages installed.
        Maybe we need a packages object, but this routine at least keeps the detail in one place.

        Or maybe we need an unacceptable_states lists.
        :return:
        """
        if self.ntp_configuration.host.state in ["unconfigured", "undeployed"]:
            return DependOn(self.ntp_configuration.host, "packages_installed")
        else:
            return DependAll()


class UnconfigureNTPStep(Step):
    idempotent = True

    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(kwargs["fqdn"], "configure_ntp", None)


class UnconfigureNTPJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(NTPConfiguration, "configured", "unconfigured")
    stateful_object = "ntp_configuration"
    ntp_configuration = models.ForeignKey(NTPConfiguration, on_delete=CASCADE)
    state_verb = "Unconfigure NTP"

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unconfigure_ntp"]

    def description(self):
        return "Unconfigure Ntp on {}".format(self.ntp_configuration.host)

    def get_steps(self):
        fqdn = self.ntp_configuration.host.fqdn

        return [(UnconfigureNTPStep, {"fqdn": fqdn}), (RestartNtpStep, {"fqdn": fqdn})]
