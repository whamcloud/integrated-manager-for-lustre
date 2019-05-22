# Copyright (c) 2019 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import logging

from django.db import models

from chroma_core.lib.cache import ObjectCache
from chroma_core.models.jobs import StatefulObject
from chroma_core.lib.job import Step, job_log, DependOn, DependAll, DependAny
from chroma_core.models import Job
from chroma_core.models import StateChangeJob, StateLock
from chroma_help.help import help_text
from chroma_core.models import AlertStateBase
from chroma_core.models import AlertEvent


class StratagemConfiguration(StatefulObject):
    id = models.IntegerField(primary_key=True, default=1, null=False)
    interval = models.IntegerField(help_text="Interval value in seconds between each stratagem execution", null=False)
    report_duration = models.IntegerField(
        help_text="Interval value in seconds between stratagem report execution", null=False
    )
    report_duration_active = models.BooleanField(
        default=False, help_text="Indicates if the report should execute at the given interval"
    )
    purge_duration = models.IntegerField(help_text="Interval value in seconds between stratagem purges", null=False)
    purge_duration_active = models.BooleanField(
        default=False, help_text="Indicates if the purge should execute at the given interval"
    )

    states = ["unconfigured", "configured"]
    initial_state = "unconfigured"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class StratagemUnconfiguredAlert(AlertStateBase):
    default_severity = logging.ERROR

    def alert_message(self):
        return "Stratagem did not configure correctly"

    class Meta:
        app_label = "chroma_core"

    def end_event(self):
        return AlertEvent(
            message_str="%s started" % self.alert_item,
            alert_item=self.alert_item.primary_host,
            alert=self,
            severity=logging.INFO,
        )

    def affected_targets(self, affect_target):
        affect_target(self.alert_item)


class ConfigureStratagemTimerStep(Step):
    def run(self, kwargs):
        job_log.debug("Create stratagem timer step kwargs: {}".format(kwargs))


class ConfigureStratagemJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(StratagemConfiguration, "unconfigured", "configured")
    stateful_object = "stratagem_configuration"
    stratagem_configuration = models.ForeignKey(StratagemConfiguration)

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Configure Stratagem"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_stratagem_long"]

    def description(self):
        return help_text["configure_stratagem_description"]

    def get_steps(self):
        steps = [(ConfigureStratagemTimerStep, {})]

        return steps
