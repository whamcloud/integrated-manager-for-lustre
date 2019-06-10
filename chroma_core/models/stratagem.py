# Copyright (c) 2019 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import logging
import json
from toolz.functoolz import pipe, partial

from django.db import models

from chroma_core.lib.cache import ObjectCache
from chroma_core.models.jobs import StatefulObject
from chroma_core.lib.job import Step, job_log, DependOn, DependAll, DependAny
from chroma_core.models import Job
from chroma_core.models import StateChangeJob, StateLock
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
    def run(self, args):
        prev_result = args["prev_result"]
        host = args["host"]
        path = args["path"]
        target_name = args["target_name"]
        report_duration = args["report_duration"]
        report_duration_active = args["report_duration_active"].lower() == 'true'
        purge_duration = args["purge_duration"]
        purge_duration_active = args["purge_duration_active"].lower() == 'true'

        def _get_body(mount_point, report_duration, report_duration_active, purge_duration, purge_duration_active):

            rule_map = {
                "fids_expiring_soon": report_duration_active,
                "fids_expired": purge_duration_active
            }

            warn_purge_times = {
                "rules": map(lambda rule, rule_map=rule_map: rule_map[rule.get("argument")], [
                    {
                        "action": "LAT_SHELL_CMD_FID",
                        "expression": "< atime - sys_time {}".format(report_duration),
                        "argument": "fids_expiring_soon",
                    },
                    {
                        "action": "LAT_SHELL_CMD_FID",
                        "expression": "< atime - sys_time {}".format(purge_duration),
                        "argument": "fids_expired",
                    }
                ]),
                "name": "warn_purge_times",
            }

            return {
                "dump_flist": False,
                "device": {"path": path, "groups": ["size_distribution", "warn_purge_times"]},
                "groups": [
                    {
                        "rules": [
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "< size 1048576",
                                "argument": "SIZE < 1M",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "&& >= size 1048576 < size 1048576000",
                                "argument": "1M <= SIZE < 1G",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": ">= size 1048576000",
                                "argument": "SIZE >= 1G",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": ">= size 1048576000000",
                                "argument": "SIZE >= 1T",
                            },
                        ],
                        "name": "size_distribution",
                    },
                    warn_purge_times
                ]
            }

        def get_column_length(rows, col_name):
            return pipe(
                rows,
                partial(map, lambda row, col_name=col_name: len(str(row.get(col_name)))),
                max
            )

        def generate_border(max_name_length, max_count_length):
            return '+' + ("-" * (max_name_length + 2)) + '+' + ("-" * (max_count_length + 2)) + '+'

        def generate_row(max_name_length, max_count_length, row):
            name = row.get('name')
            count = str(row.get('count'))

            return "| {}{} | {}{} |\n{}".format(
                name,  
                " " * (max_name_length - len(name)), 
                count, 
                " " * (max_count_length - len(count)), 
                generate_border(max_name_length, max_count_length)
            )
            

        def generate_rows(rows):
            max_name_length = get_column_length(rows, 'name')
            max_count_length = get_column_length(rows, 'count')

            return "{}\n{}".format(
                generate_border(max_name_length, max_count_length), 
                "\n".join(
                    map(partial(generate_row, max_name_length, max_count_length), rows)
                )
            )

        def generate_group_counter_output(group):
            group_name = group.get('name')
            table = generate_rows(group.get('counters'))

            return "<strong>Group</strong>: <span class='text-warning'>{}</span>\n\n{}".format(group_name, table)


        def generate_output_from_results(result):
            results_path = result[0]
            group_counters_output = map(generate_group_counter_output, result[1].get('group_counters'))

            return "<span class='text-success'><i class='fa fa-check'></i> Scan finished for target {}.</span>\nResults located in {}\n\n{}".format(
                target_name, 
                results_path, 
                "\n\n".join(group_counters_output)
            )


        body = _get_body(path, report_duration, report_duration_active, purge_duration, purge_duration_active))
        result = self.invoke_rust_agent_expect_result(host, "start_scan_stratagem", body)

        self.log(generate_output_from_results(result))

        return result


class StreamFidlistStep(Step):
    def run(self, args):
        scan_result = args["prev_result"]
        host = args["host"]
        unique_id = args["uuid"]

        fid_dir, stratagem_result, mailbox_files = scan_result

        mailbox_files = map(lambda (path, label): (path, "{}-{}".format(unique_id, label)) , mailbox_files)
        result = self.invoke_rust_agent_expect_result(host, "stream_fidlists_stratagem", mailbox_files)

        self.log("Called stream_fidlists_stratagem with:\n{}\nResult:\n{}".format(mailbox_files, result))

        return result


class RunStratagemJob(Job):
    mdt_id = models.IntegerField()
    uuid = models.CharField(max_length=64, null=False, default="")
    interval = models.IntegerField()
    report_duration = models.IntegerField()
    report_duration_active = models.BooleanField(default=False, help_text="Report duration active")
    purge_duration = models.IntegerField()
    purge_duration_active = models.BooleanField(default=False, help_text="Purge duration active")
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

        return [
            (RunStratagemStep, {
                "host": self.fqdn,
                "path": path, 
                "target_name": self.target_name,
                "report_duration": self.report_duration,
                "report_duration_active": self.report_duration_active,
                "purge_duration": self.purge_duration,
                "purge_duration_active": self.purge_duration_active
            }), 
            (StreamFidlistStep, {
                "host": self.fqdn, 
                "uuid": self.uuid
            })
        ]


class SendStratagemResultsToClientJob(Job):

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, self):
        return "Sending stratagem results to client"

    def description(self):
        return "Sending stratagem results to client"