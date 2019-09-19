# Copyright (c) 2019 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import logging
import os

from os import path
from toolz.functoolz import pipe, partial, flip
from settings import MAILBOX_PATH
from django.db import models

from chroma_core.lib.cache import ObjectCache
from chroma_core.models.jobs import StatefulObject
from chroma_core.models.utils import DeletableMetaclass
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
from chroma_core.lib.util import CommandLine

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
    filesystem = models.ForeignKey("ManagedFilesystem", null=False)
    interval = models.BigIntegerField(
        help_text="Interval value in milliseconds between each stratagem execution", null=False
    )
    report_duration = models.BigIntegerField(
        help_text="Interval value in milliseconds between stratagem report execution", null=True
    )
    purge_duration = models.BigIntegerField(
        help_text="Interval value in milliseconds between stratagem purges", null=True
    )

    def get_label(self):
        return "Stratagem Configuration"

    def get_deps(self, state=None):
        if not state:
            state = self.state

        deps = []
        if state != "removed":
            # Depend on the filesystem being available.
            deps.append(DependOn(self.filesystem, "available", fix_state="unconfigured"))

            # move to the removed state if the filesystem is removed.
            deps.append(
                DependOn(
                    self.filesystem,
                    "available",
                    acceptable_states=list(set(self.filesystem.states) - set(["removed", "forgotten"])),
                    fix_state="removed",
                )
            )

        return DependAll(deps)

    def filter_by_fs(fs):
        return ObjectCache.get(StratagemConfiguration, lambda sc, fs=fs: sc.filesystem.id == fs.id)

    reverse_deps = {"ManagedFilesystem": filter_by_fs}

    states = ["unconfigured", "configured", "removed"]
    initial_state = "unconfigured"

    __metaclass__ = DeletableMetaclass

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


def unit_name(fid):
    return "iml-stratagem-{}".format(fid)


def timer_file(fid):
    return "/etc/systemd/system/{}.timer".format(unit_name(fid))


def service_file(fid):
    return "/etc/systemd/system/{}.service".format(unit_name(fid))


class ConfigureStratagemTimerStep(Step, CommandLine):
    def run(self, kwargs):
        job_log.debug("Configure stratagem timer step kwargs: {}".format(kwargs))
        # Create systemd timer

        config = kwargs["config"]

        with open(timer_file(config.id), "w") as fn:
            fn.write(
                "#  This file is part of IML\n"
                "#  This file will be overwritten automatically\n"
                "\n[Unit]\n"
                "Description=Start Stratagem run on {}\n"
                "\n[Timer]\n"
                "OnActiveSec={}\n"
                "OnUnitActiveSec={}\n".format(config.filesystem.id, config.interval / 1000, config.interval / 1000)
            )

        iml_cmd = "/usr/bin/iml stratagem scan --filesystem {}".format(config.filesystem.id)
        if config.report_duration is not None and config.report_duration >= 0:
            iml_cmd += " --report {}s".format(config.report_duration / 1000)
        if config.purge_duration is not None and config.purge_duration >= 0:
            iml_cmd += " --purge {}s".format(config.purge_duration / 1000)
        with open(service_file(config.id), "w") as fn:
            fn.write(
                "#  This file is part of IML\n"
                "#  This file will be overwritten automatically\n"
                "\n[Unit]\n"
                "Description=Start Stratagem run on {}\n"
                "After=iml-manager.target\n"
                "\n[Service]\n"
                "Type=oneshot\n"
                "ExecStart={}\n".format(config.filesystem.id, iml_cmd)
            )
        self.try_shell(["systemctl", "daemon-reload"])
        self.try_shell(["systemctl", "enable", "--now", "{}.timer".format(unit_name(config.id))])


class UnconfigureStratagemTimerStep(Step, CommandLine):
    def run(self, kwargs):
        job_log.debug("Unconfigure stratagem timer step kwargs: {}".format(kwargs))

        config = kwargs["config"]

        self.try_shell(["systemctl", "disable", "--now", "{}.timer".format(unit_name(config.id))])

        os.unlink(timer_file(config.id))
        os.unlink(service_file(config.id))
        self.try_shell(["systemctl", "daemon-reload"])


class ForgetStratagemConfigurationJob(StateChangeJob):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, self):
        return "Forget the stratagem configuration for filesystem"

    def description(self):
        return self.long_description(self)

    def get_requires_confirmation(self):
        return True

    def on_success(self):
        self.stratagem_configuration.mark_deleted()
        job_log.debug("forgetting stratagem configuration")

        super(ForgetStratagemConfigurationJob, self).on_success()

    state_transition = StateChangeJob.StateTransition(StratagemConfiguration, "unconfigured", "removed")
    stateful_object = "stratagem_configuration"
    stratagem_configuration = models.ForeignKey(StratagemConfiguration)
    state_verb = "Forget"


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
        return help_text["configure_stratagem_long"]

    def get_steps(self):
        steps = []
        if os.path.exists(timer_file(self.stratagem_configuration.id)):
            steps.append((UnconfigureStratagemTimerStep, {"config": self.stratagem_configuration}))
        steps.append((ConfigureStratagemTimerStep, {"config": self.stratagem_configuration}))

        return steps


class UnconfigureStratagemJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(StratagemConfiguration, "configured", "unconfigured")
    stateful_object = "stratagem_configuration"
    stratagem_configuration = models.ForeignKey(StratagemConfiguration)
    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Unconfigure"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return "Unconfigure Stratagem for the given filesystem"

    def description(self):
        return "Unconfigure Stratagem for the given filesystem"

    def get_steps(self):
        steps = [(UnconfigureStratagemTimerStep, {"config": self.stratagem_configuration})]

        return steps


class DeleteStratagemStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        x = kwargs["stratagem_configuration"]
        x.mark_deleted()
        x.save()


class RemoveStratagemJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(StratagemConfiguration, "unconfigured", "removed")
    stateful_object = "stratagem_configuration"
    stratagem_configuration = models.ForeignKey(StratagemConfiguration)
    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    requires_confirmation = False
    state_verb = "Remove"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return "Remove Stratagem for the given filesystem"

    def description(self):
        return "Remove Stratagem for the given filesystem"

    def get_steps(self):
        return [(DeleteStratagemStep, {"stratagem_configuration": self.stratagem_configuration})]

    def get_deps(self):
        return DependOn(self.stratagem_configuration, "unconfigured")


class RunStratagemStep(Step):
    def run(self, args):
        host = args["host"]
        path = args["path"]
        target_name = args["target_name"]
        report_duration = args["report_duration"]
        purge_duration = args["purge_duration"]

        def calc_warn_duration(report_duration, purge_duration):
            if report_duration is not None and purge_duration is not None:
                return "&& != type S_IFDIR && < atime - sys_time {} > atime - sys_time {}".format(
                    report_duration, purge_duration
                )

            return "&& != type S_IFDIR < atime - sys_time {}".format(report_duration or 0)

        def get_body(mount_point, report_duration, purge_duration):
            rule_map = {
                "fids_expiring_soon": report_duration is not None and "warn_fids",
                "fids_expired": purge_duration is not None and "purge_fids",
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
                                "counter_name": "fids_expiring_soon",
                            }
                        ],
                    },
                    {
                        "name": "purge_fids",
                        "rules": [
                            {
                                "action": "LAT_SHELL_CMD_FID",
                                "expression": "&& != type S_IFDIR < atime - sys_time {}".format(purge_duration),
                                "argument": "fids_expired",
                                "counter_name": "fids_expired",
                            }
                        ],
                    },
                ],
            )

            return {
                "flist_type": "none",
                "summarize_size": True,
                "device": {"path": path, "groups": groups},
                "groups": [
                    {
                        "rules": [
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "&& < size 1048576 != type S_IFDIR",
                                "argument": "SIZE < 1M",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "&& >= size 1048576000000 != type S_IFDIR",
                                "argument": "SIZE >= 1T",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "&& >= size 1048576000 != type S_IFDIR",
                                "argument": "SIZE >= 1G",
                            },
                            {
                                "action": "LAT_COUNTER_INC",
                                "expression": "&& >= size 1048576 != type S_IFDIR",
                                "argument": "1M <= SIZE < 1G",
                            },
                        ],
                        "name": "size_distribution",
                    },
                    {
                        "rules": [
                            {
                                "action": "LAT_ATTR_CLASSIFY",
                                "expression": "!= type S_IFDIR",
                                "argument": "uid",
                                "counter_name": "top_inode_users",
                            }
                        ],
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
        fs_name = args["fs_name"]

        _, stratagem_result, mailbox_files = scan_result

        # Send stratagem_results to time series database
        influx_entries = parse_stratagem_results_to_influx(temp_stratagem_measurement, fs_name, stratagem_result)
        job_log.debug("influx_entries: {}".format(influx_entries))

        record_stratagem_point("\n".join(influx_entries))

        mailbox_files = map(lambda xs: (xs[0], "{}-{}".format(unique_id, xs[1])), mailbox_files)
        result = self.invoke_rust_agent_expect_result(host, "stream_fidlists_stratagem", mailbox_files)

        return result


class RunStratagemJob(Job):
    filesystem = models.ForeignKey("ManagedFilesystem", null=False)
    mdt_id = models.IntegerField()
    uuid = models.CharField(max_length=64, null=False, default="")
    report_duration = models.BigIntegerField(null=True)
    purge_duration = models.BigIntegerField(null=True)
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

    def create_locks(self):
        locks = super(RunStratagemJob, self).create_locks()
        locks.append(StateLock(job=self, locked_item=self.filesystem, write=False))

        return locks

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
            (StreamFidlistStep, {"host": self.fqdn, "uuid": self.uuid, "fs_name": self.filesystem.name}),
        ]


class AggregateStratagemResultsStep(Step):
    def run(self, args):
        clear_scan_results(args["clear_measurement_query"].format(args["fs_name"]))
        aggregated = aggregate_points(args["aggregate_query"])
        influx_entries = submit_aggregated_data(args["measurement"], args["fs_name"], aggregated)
        clear_scan_results(args["clear_temp_measurement_query"])

        self.log(u"\u2713 Aggregated Stratagem counts and submitted to time series database.")

        return influx_entries


class AggregateStratagemResultsJob(Job):
    fs_name = models.CharField(max_length=8, null=False)

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
                    "clear_measurement_query": "DELETE FROM stratagem_scan WHERE fs_name='{}'",
                    "clear_temp_measurement_query": "DROP MEASUREMENT temp_stratagem_scan",
                    "measurement": "stratagem_scan",
                    "fs_name": self.fs_name,
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

        action_list = filter(lambda (_, xs): path.exists("{}/{}".format(MAILBOX_PATH, xs[1])), action_list)

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
    filesystem = models.ForeignKey("ManagedFilesystem", null=False)
    uuid = models.CharField(max_length=64, null=False, default="")
    report_duration = models.BigIntegerField(null=True)
    purge_duration = models.BigIntegerField(null=True)

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
        client_mount = LustreClientMount.objects.get(host_id=client_host.id, filesystem_id=self.filesystem.id)

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
