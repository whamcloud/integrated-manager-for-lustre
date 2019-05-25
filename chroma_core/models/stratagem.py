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
from chroma_core.models import AlertStateBase, AlertEvent, ManagedHost, ManagedMdt, ManagedTargetMount


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
        # Create systemd timer


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


class RunStratagemStep(Step):
    database = True

    def run(self, kwargs):
        def _get_body(mount_point):
            return {
                "dump_flist": False,
                "device": {"path": mount_point, "groups": ["size_distribution", "warn_purge_times"]},
                "groups": [
                    {
                        "rules": [
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "< size 1048576",
                                "argument": "smaller_than_1M",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "&& >= size 1048576 < size 1048576000",
                                "argument": "not_smaller_than_1M_and_smaller_than_1G",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": ">= size 1048576000",
                                "argument": "not_smaller_than_1G",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": ">= size 1048576000000",
                                "argument": "not_smaller_than_1T",
                            },
                        ],
                        "name": "size_distribution",
                    },
                    {
                        "rules": [
                            {
                                "action": "LAT_SHELL_CMD_FID",
                                "expression": "< atime - sys_time 18000000",
                                "argument": "fids_expiring_soon",
                            },
                            {
                                "action": "LAT_SHELL_CMD_FID",
                                "expression": "< atime - sys_time 5184000000",
                                "argument": "fids_expired",
                            },
                        ],
                        "name": "warn_purge_times",
                    },
                ],
            }

        for mdt in ManagedMdt.objects.all():
            target = ManagedTargetMount.objects.get(id=mdt.active_mount_id)
            host = ManagedHost.objects.get(id=target.host_id)

            body = _get_body(target.mount_point)

            result = self.invoke_rust_agent(host.fqdn, "start_scan_stratagem", body)
            # Was the result an error? If so, handle it.
            job_log.warning("Run stratagem result: {}".format(result))

            # next step is to stream the results to the mailbox


class RunStratagemJob(Job):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls):
        return help_text["run_stratagem"]

    def description(self):
        return self.long_description()

    def get_steps(self):
        return [(RunStratagemStep, {})]

