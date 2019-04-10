# Copyright (c) 2019 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from django.db import models


class Stratagem(DeletableStatefulObject):
    interval = models.IntegerField(help_text="Interval value in which a stratagem run will execute")
    report_duration = models.IntegerField(help_text="Interval value in which stratagem reports are run")
    report_duration_active = models.BooleanField(
        default=False, help_text="Indicates if the report should execute at the given interval"
    )
    purge_duration = models.IntegerField(help_text="Interval value in which a stratagem purge will execute")
    purge_duration_active = models.BooleanField(
        default=False, help_text="Indicates if the purge should execute at the given interval"
    )
    states = ["unconfigured", "configured"]
    initial_state = "unconfigured"


class ConfigureSettingsStep(Step):
    def run(self, kwargs):
        print "Configure settings Step kwargs: {}".format(kwargs)


class ConfigureSystemdTimerStep(Step):
    def run(self, kwargs):
        print "Create systemd time Step kwargs: {}".format(kwargs)



class ConfigureStratagemJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Stratagem, "unconfigured", "configured")
    stateful_object = "stratagem"
    stratagem = models.ForeignKey(Stratagem)
    state_verb = help_text["configue_stratagem"]

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_stratagem_long"]

    def description(self):
        return help_text["configure_stratagem_description"]

    def get_steps(self):
        self._so_cache = self.stratagem = ObjectCache.update(self.stratagem)

        steps = [
            (ConfigureSettingsStep, {
                "interval": 30,
                "report_duration": 30,
                "report_duration_active": True,
                "purge_duration": 0,
                "purge_duration_active": False
            }),
            (ConfigureSystemdTimerStep, {})
        ]

        return steps

    @classmethod
    def can_run(cls, host):
        return host.state == "unconfigured"
