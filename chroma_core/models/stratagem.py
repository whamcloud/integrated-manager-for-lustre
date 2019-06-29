# Copyright (c) 2019 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import logging
import json
from toolz.functoolz import pipe, partial, flip

from django.db import models

from chroma_core.lib.cache import ObjectCache
from chroma_core.models.jobs import StatefulObject
from chroma_core.lib.job import Step, job_log, DependOn, DependAll, DependAny
from chroma_core.lib.stratagem import (
    parse_stratagem_results_to_influx,
    record_stratagem_point,
    clear_scan_results,
    temp_stratagem_measurement,
    stratagem_measurement,
    aggregate_points,
    submit_aggregated_data,
)

from chroma_core.models import Job
from chroma_core.models import StateChangeJob, StateLock, StepResult, LustreClientMount
from chroma_help.help import help_text
from chroma_core.models import (
    AlertStateBase,
    AlertEvent,
    ManagedHost,
    ManagedMdt,
    ManagedTarget,
    ManagedTargetMount,
    Volume,
    VolumeNode,
    StorageResourceRecord,
)


class StratagemConfiguration(StatefulObject):
    filesystem_id = models.IntegerField(
        help_text="The filesystem id associated with the stratagem configuration", null=False
    )
    interval = models.IntegerField(help_text="Interval value in seconds between each stratagem execution", null=False)
    report_duration = models.IntegerField(
        help_text="Interval value in seconds between stratagem report execution", null=True
    )
    purge_duration = models.IntegerField(help_text="Interval value in seconds between stratagem purges", null=True)

    states = ["unconfigured", "configured"]
    initial_state = "unconfigured"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


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
    def run(self, args):
        host = args["host"]
        path = args["path"]
        target_name = args["target_name"]
        report_duration = args["report_duration"]
        purge_duration = args["purge_duration"]

        def calc_warn_duration(report_duration, purge_duration):
            if report_duration is not None and purge_duration is not None:
                return "(&& < atime - sys_time {} > atime - sys_time {})".format(report_duration, purge_duration)

            return "< atime - sys_time {}".format(report_duration or 0)

        def get_body(mount_point, report_duration, purge_duration):
            rule_map = {
                "fids_expiring_soon": report_duration != None and "warn_fids",
                "fids_expired": purge_duration != None and "purge_fids",
            }

            groups = ["size_distribution", "user_distribution"] + filter(bool, rule_map.values())

            additional_groups = filter(
                lambda group, rule_map=rule_map: rule_map.get(group.get("rules")[0].get("argument")),
                [
                    {
                        "name": "warn_fids",
                        "rules": [
                            {
                                "action": "LAT_SHELL_CMD_FID",
                                "expression": calc_warn_duration(report_duration, purge_duration),
                                "argument": "fids_expiring_soon",
                            }
                        ],
                    },
                    {
                        "name": "purge_fids",
                        "rules": [
                            {
                                "action": "LAT_SHELL_CMD_FID",
                                "expression": "< atime - sys_time {}".format(purge_duration),
                                "argument": "fids_expired",
                            }
                        ],
                    },
                ],
            )

            return {
                "dump_flist": False,
                "device": {"path": path, "groups": groups},
                "groups": [
                    {
                        "rules": [
                            {"action": "LAT_COUNTER_INC", "expression": "< size 1048576", "argument": "SIZE < 1M"},
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "&& >= size 1048576 < size 1048576000",
                                "argument": "1M <= SIZE < 1G",
                            },
                            {"action": "LAT_COUNTER_INC", "expression": ">= size 1048576000", "argument": "SIZE >= 1G"},
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": ">= size 1048576000000",
                                "argument": "SIZE >= 1T",
                            },
                        ],
                        "name": "size_distribution",
                    },
                    {
                        "rules": [{"action": "LAT_ATTR_CLASSIFY", "expression": "1", "argument": "uid"}],
                        "name": "user_distribution",
                    },
                ]
                + additional_groups,
            }

        def generate_output_from_results(result):
            return u"\u2713 Scan finished for target {}.\nResults located in {}".format(target_name, result[0])

        body = get_body(path, report_duration, purge_duration)
        result = self.invoke_rust_agent_expect_result(host, "start_scan_stratagem", body)

        self.log(generate_output_from_results(result))

        return result


class StreamFidlistStep(Step):
    def run(self, args):
        scan_result = args["prev_result"]
        host = args["host"]
        unique_id = args["uuid"]

        _, stratagem_result, mailbox_files = scan_result

        # Send stratagem_results to time series database
        influx_entries = parse_stratagem_results_to_influx(temp_stratagem_measurement, stratagem_result)
        job_log.debug("influx_entries: {}".format(influx_entries))

        record_stratagem_point("\n".join(influx_entries))

        mailbox_files = map(lambda xs: (xs[0], "{}-{}".format(unique_id, xs[1])), mailbox_files)
        result = self.invoke_rust_agent_expect_result(host, "stream_fidlists_stratagem", mailbox_files)

        return result


class RunStratagemJob(Job):
    mdt_id = models.IntegerField()
    uuid = models.CharField(max_length=64, null=False, default="")
    report_duration = models.IntegerField(null=True)
    purge_duration = models.IntegerField(null=True)
    fqdn = models.CharField(max_length=255, null=False, default="")
    target_name = models.CharField(max_length=64, null=False, default="")
    filesystem_type = models.CharField(max_length=32, null=False, default="")
    target_mount_point = models.CharField(max_length=512, null=False, default="")
    device_path = models.CharField(max_length=512, null=False, default="")

    def __init__(self, *args, **kwargs):
        if "mdt_id" not in kwargs or "uuid" not in kwargs:
            super(RunStratagemJob, self).__init__(*args, **kwargs)
        else:
            mdt = ManagedMdt.objects.get(id=kwargs["mdt_id"])
            target_mount = ManagedTargetMount.objects.get(id=mdt.active_mount_id)
            volume_node = VolumeNode.objects.get(id=target_mount.volume_node_id)
            volume = Volume.objects.get(id=mdt.volume_id)
            host = ManagedHost.objects.get(id=target_mount.host_id)

            kwargs["fqdn"] = host.fqdn
            kwargs["target_name"] = mdt.name
            kwargs["filesystem_type"] = volume.filesystem_type
            kwargs["target_mount_point"] = target_mount.mount_point
            kwargs["device_path"] = volume_node.path

            super(RunStratagemJob, self).__init__(*args, **kwargs)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, self):
        return help_text["run_stratagem"].format(self.target_name)

    def description(self):
        return self.long_description(self)

    def get_steps(self):

        if self.filesystem_type.lower() == "zfs":
            path = self.target_mount_point
        else:
            path = self.device_path

        clear_scan_results("DROP MEASUREMENT temp_stratagem_scan")
        return [
            (
                RunStratagemStep,
                {
                    "host": self.fqdn,
                    "path": path,
                    "target_name": self.target_name,
                    "report_duration": self.report_duration,
                    "purge_duration": self.purge_duration,
                },
            ),
            (StreamFidlistStep, {"host": self.fqdn, "uuid": self.uuid}),
        ]


class AggregateStratagemResultsStep(Step):
    def run(self, args):
        clear_scan_results(args["clear_measurement_query"])
        aggregated = aggregate_points(args["aggregate_query"])
        influx_entries = submit_aggregated_data(args["measurement"], aggregated)
        clear_scan_results(args["clear_temp_measurement_query"])

        self.log(u"\u2713 Aggregated Stratagem counts and submitted to time series database.")

        return influx_entries


class AggregateStratagemResultsJob(Job):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(self):
        return "Aggregating stratagem scan results in influxdb."

    def description(self):
        return "Aggregating stratagem scan results in influxdb."

    def get_steps(self):
        return [
            (
                AggregateStratagemResultsStep,
                {
                    "aggregate_query": "SELECT * FROM temp_stratagem_scan",
                    "clear_measurement_query": "DROP MEASUREMENT stratagem_scan",
                    "clear_temp_measurement_query": "DROP MEASUREMENT temp_stratagem_scan",
                    "measurement": "stratagem_scan",
                },
            )
        ]


class SendResultsToClientStep(Step):
    def run(self, args):
        host, mount_point, uuid, report_duration, purge_duration = args["client_args"]

        if report_duration is None and purge_duration is None:
            return

        action_list = [
            (label, args)
            for (duration, label, args) in [
                (
                    purge_duration,
                    "action_purge_stratagem",
                    (mount_point, "{}-{}".format(uuid, "purge_fids-fids_expired")),
                ),
                (
                    report_duration,
                    "action_warning_stratagem",
                    (mount_point, "{}-{}".format(uuid, "warn_fids-fids_expiring_soon")),
                ),
            ]
            if duration is not None
        ]

        file_location = pipe(
            action_list,
            partial(map, lambda xs, host=host: self.invoke_rust_agent_expect_result(host, xs[0], xs[1])),
            partial(filter, bool),
            iter,
            partial(flip, next, None),
        )

        if file_location:
            self.log(u"\u2713 Scan results sent to client under:\n{}".format(file_location))

        return file_location


class SendStratagemResultsToClientJob(Job):
    uuid = models.CharField(max_length=64, null=False, default="")
    report_duration = models.IntegerField(null=True)
    purge_duration = models.IntegerField(null=True)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(self):
        return "Sending stratagem results to client"

    def description(self):
        return "Sending stratagem results to client"

    def get_steps(self):
        client_host = ManagedHost.objects.get(server_profile_id="stratagem_client")
        client_mount = LustreClientMount.objects.get(host_id=client_host.id)

        return [
            (
                SendResultsToClientStep,
                {
                    "client_args": (
                        client_host.fqdn,
                        client_mount.mountpoint,
                        self.uuid,
                        self.report_duration,
                        self.purge_duration,
                    )
                },
            )
        ]
