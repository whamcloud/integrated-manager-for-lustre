# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import os
import requests

from settings import TIMER_PROXY_PASS
from django.db import models
from django.db.models import CASCADE, Q
from django.contrib.postgres import fields
from chroma_core.lib.cache import ObjectCache
from chroma_core.models.jobs import StatefulObject
from chroma_core.models.utils import DeletableMetaclass
from chroma_core.lib.job import Step, job_log, DependOn, DependAll
from chroma_core.lib.stratagem import (
    parse_stratagem_results_to_influx,
    record_stratagem_point,
    clear_scan_results,
    temp_stratagem_measurement,
    aggregate_points,
    submit_aggregated_data,
)
from chroma_core.lib.util import CommandLine, runningInDocker
from chroma_core.models.jobs import Job, StateChangeJob, StateLock
from chroma_help.help import help_text
from chroma_core.models.filesystem import ManagedFilesystem


class StratagemConfiguration(StatefulObject):
    filesystem = models.ForeignKey("ManagedFilesystem", null=False, on_delete=CASCADE)
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
    return "emf-stratagem-{}".format(fid)


def timer_file(fid):
    return "/etc/systemd/system/{}.timer".format(unit_name(fid))


def service_file(fid):
    return "/etc/systemd/system/{}.service".format(unit_name(fid))


class ConfigureStratagemTimerStep(Step, CommandLine):
    def get_run_stratagem_command(self, cmd, config):
        emf_cmd = "{} --filesystem {}".format(cmd, config.filesystem.id)
        if config.report_duration is not None and config.report_duration >= 0:
            emf_cmd += " --report {}s".format(config.report_duration / 1000)
        if config.purge_duration is not None and config.purge_duration >= 0:
            emf_cmd += " --purge {}s".format(config.purge_duration / 1000)

        return emf_cmd

    def run(self, kwargs):
        job_log.debug("Configure stratagem timer step kwargs: {}".format(kwargs))
        # Create systemd timer

        config = kwargs["config"]

        emf_cmd = self.get_run_stratagem_command("/usr/bin/emf stratagem scan", config)

        interval_in_seconds = config.interval / 1000
        # Create timer file
        timer_config = """# This file is part of EMF
# This file will be overwritten automatically

[Unit]
Description=Start Stratagem run on {}

[Timer]
OnActiveSec={}
OnUnitActiveSec={}
AccuracySec=1us
Persistent=true

[Install]
WantedBy=timers.target
""".format(
            config.filesystem.id, interval_in_seconds, interval_in_seconds
        )

        service_config = """# This file is part of EMF
# This file will be overwritten automatically

[Unit]
Description=Start Stratagem run on {}
{}

[Service]
Type=oneshot
EnvironmentFile=/var/lib/chroma/emf-settings.conf
ExecStart={}
""".format(
            config.filesystem.id, "After=emf-manager.target" if not runningInDocker() else "", emf_cmd
        )

        post_data = {
            "config_id": str(config.id),
            "file_prefix": "emf-stratagem",
            "timer_config": timer_config,
            "service_config": service_config,
        }

        result = requests.put("{}/configure/".format(TIMER_PROXY_PASS), json=post_data)

        if not result.ok:
            raise RuntimeError(result.reason)


class UnconfigureStratagemTimerStep(Step, CommandLine):
    def run(self, kwargs):
        job_log.debug("Unconfigure stratagem timer step kwargs: {}".format(kwargs))

        config = kwargs["config"]

        if runningInDocker():
            result = requests.delete("{}/unconfigure/emf-stratagem/{}".format(TIMER_PROXY_PASS, config.id))

            if not result.ok:
                raise RuntimeError(result.reason)
        else:
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
    stratagem_configuration = models.ForeignKey(StratagemConfiguration, on_delete=CASCADE)
    state_verb = "Forget"


class ConfigureStratagemJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(StratagemConfiguration, "unconfigured", "configured")
    stateful_object = "stratagem_configuration"
    stratagem_configuration = models.ForeignKey(StratagemConfiguration, on_delete=CASCADE)

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
    stratagem_configuration = models.ForeignKey(StratagemConfiguration, on_delete=CASCADE)
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
    stratagem_configuration = models.ForeignKey(StratagemConfiguration, on_delete=CASCADE)
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
        pass


class BuildScanReportStep(Step):
    def run(self, args):
        scan_result = args["prev_result"]
        fs_name = args["fs_name"]

        _, stratagem_result, _ = scan_result

        # Send stratagem_results to time series database
        influx_entries = parse_stratagem_results_to_influx(temp_stratagem_measurement, fs_name, stratagem_result)
        job_log.debug("influx_entries: {}".format(influx_entries))

        record_stratagem_point("\n".join(influx_entries))

        return args["prev_result"]


class StreamFidlistStep(Step):
    def run(self, args):
        scan_result = args["prev_result"]
        host = args["host"]
        unique_id = args["uuid"]

        _, _, mailbox_files = scan_result

        mailbox_files = map(lambda xs: (xs[0], "{}-{}".format(unique_id, xs[1])), mailbox_files)
        result = self.invoke_rust_agent_expect_result(host, "stream_fidlists_stratagem", mailbox_files)

        self.log(u"\u2713 Scan results sent to client under:\n{}".format("\n".join(xs[1] for xs in mailbox_files)))

        return result


class ClearOldStratagemDataJob(Job):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(self):
        return "Removing old Stratagem data"

    def description(self):
        return "Removing old Stratagem data"

    def get_steps(self):
        return [(ClearOldStratagemDataStep, {})]


class ClearOldStratagemDataStep(Step):
    def run(self, kwargs):
        clear_scan_results("DROP MEASUREMENT temp_stratagem_scan")


class FastFileScanMdtJob(Job):
    fqdn = models.CharField(max_length=256, null=False, help_text="MDT host to perform scan on")
    uuid = models.CharField(max_length=64, null=False)
    fsname = models.CharField(max_length=8, null=False)
    config = fields.JSONField(null=False)

    @classmethod
    def long_description(self):
        return "Scanning MDT"

    def description(self):
        return "Scan with the given config on the given host"

    def create_locks(self):
        return [StateLock(job=self, locked_item=ManagedFilesystem.objects.get(name=self.fsname), write=False)]

    def get_steps(self):
        return [
            (ScanMdtStep, {"host": self.fqdn, "config": self.config}),
            (BuildScanReportStep, {"fs_name": self.fsname}),
            (StreamFidlistStep, {"host": self.fqdn, "uuid": self.uuid, "fs_name": self.fsname}),
        ]


class ScanMdtJob(Job):
    fqdn = models.CharField(max_length=256, null=False, help_text="MDT host to perform scan on")
    uuid = models.CharField(max_length=64, null=False)
    fsname = models.CharField(max_length=8, null=False)
    config = fields.JSONField(null=False)

    @classmethod
    def long_description(self):
        return "Scanning MDT"

    def description(self):
        return "Scan with the given config on the given host"

    def create_locks(self):
        return [StateLock(job=self, locked_item=ManagedFilesystem.objects.get(name=self.fsname), write=False)]

    def get_steps(self):
        return [
            (ScanMdtStep, {"host": self.fqdn, "config": self.config}),
            (StreamFidlistStep, {"host": self.fqdn, "uuid": self.uuid, "fs_name": self.fsname}),
        ]


class ScanMdtStep(Step):
    def run(self, args):
        return self.invoke_rust_agent_expect_result(args["host"], "start_scan_stratagem", args["config"])


class RunStratagemJob(Job):
    filesystem = models.ForeignKey("ManagedFilesystem", null=False, on_delete=CASCADE)
    mdt_id = models.IntegerField()
    uuid = models.CharField(max_length=64, null=False, default="")
    report_duration = models.BigIntegerField(null=True)
    purge_duration = models.BigIntegerField(null=True)
    search_expression = models.TextField(null=True, default="")
    action = models.TextField(default="")
    fqdn = models.CharField(max_length=255, null=False, default="")
    target_name = models.CharField(max_length=64, null=False, default="")
    filesystem_type = models.CharField(max_length=32, null=False, default="")
    target_mount_point = models.CharField(max_length=512, null=False, default="")
    device_path = models.CharField(max_length=512, null=False, default="")

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, self):
        return help_text["run_stratagem"].format(self.target_name)

    def description(self):
        return self.long_description(self)


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
