# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import uuid
from collections import namedtuple

from django.db import models
from django.utils.timezone import now as tznow

from chroma_core.services import log_register
from chroma_core.lib.job import DependOn
from chroma_core.lib.job import DependAll
from chroma_core.lib.job import Step
from chroma_core.lib.cache import ObjectCache
from chroma_core.models.client_mount import LustreClientMount
from chroma_core.models.jobs import StateChangeJob
from chroma_core.models.jobs import StatefulObject
from chroma_core.models.jobs import Job
from chroma_core.models.jobs import AdvertisedJob
from chroma_core.models.utils import DeletableDowncastableMetaclass
from chroma_core.models.utils import CHARFIELD_MAX_LENGTH
from chroma_core.models.utils import MeasuredEntity
from chroma_help.help import help_text
from iml_common.lib.date_time import IMLDateTime

log = log_register(__name__.split(".")[-1])

# special uuid used to flag a copytool that wasn't properly registered
UNKNOWN_UUID = "00000000-0000-0000-0000-000000000000"

# poor-man's enum
OP_STATES = namedtuple("STATES", "UNKNOWN, STARTED, RUNNING, FINISHED, ERRORED")(0, 1, 2, 3, 4)
OP_TYPES = namedtuple("TYPES", "UNKNOWN, ARCHIVE, RESTORE, REMOVE")(0, 1, 2, 3)


def resolve_value(container, key):
    if container == "state":
        return OP_STATES._asdict()[key]
    elif container == "type":
        return OP_TYPES._asdict()[key]
    else:
        raise AttributeError("Unable to resolve %s[%s]" % container, key)


def resolve_key(container, value):
    if container == "state":
        return OP_STATES._fields[value]
    elif container == "type":
        return OP_TYPES._fields[value]
    else:
        raise AttributeError("Unable to resolve %s[%s]" % container, value)


class CopytoolOperation(models.Model):
    STATE_CHOICES = (
        (OP_STATES.UNKNOWN, "unknown"),
        (OP_STATES.STARTED, "Started"),
        (OP_STATES.RUNNING, "Currently"),
        (OP_STATES.FINISHED, "Finished"),
        (OP_STATES.ERRORED, "Failed while"),
    )
    TYPE_CHOICES = (
        (OP_TYPES.UNKNOWN, "unknown (file: %s)"),
        (OP_TYPES.ARCHIVE, "copying %s from Lustre to HSM backend"),
        (OP_TYPES.RESTORE, "restoring %s from HSM backend to Lustre"),
        (OP_TYPES.REMOVE, "removing %s from HSM backend"),
    )
    state = models.SmallIntegerField(choices=STATE_CHOICES, default=OP_STATES.UNKNOWN)
    type = models.SmallIntegerField(choices=TYPE_CHOICES, default=OP_TYPES.UNKNOWN)
    copytool = models.ForeignKey("Copytool", related_name="operations")
    started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    processed_bytes = models.BigIntegerField(
        null=True, blank=True, help_text="Count of bytes processed so far for running operation"
    )
    total_bytes = models.BigIntegerField(null=True, blank=True, help_text="Expected total bytes for running operation")
    path = models.CharField(max_length=CHARFIELD_MAX_LENGTH, null=True, blank=True, help_text="Lustre path of file")
    fid = models.CharField(max_length=CHARFIELD_MAX_LENGTH, null=True, blank=True, help_text="Lustre FID of file")
    info = models.CharField(max_length=256, null=True, blank=True, help_text="Additional information, if available")

    def __str__(self):
        return "%s %s" % (self.STATE_CHOICES[self.state][1], self.TYPE_CHOICES[self.type][1] % self.path)

    def update(self, updated_at, current_bytes, total_bytes):
        self.updated_at = updated_at
        self.state = OP_STATES.RUNNING
        self.total_bytes = total_bytes
        self.processed_bytes = current_bytes
        self.save()

    def finish(self, finished_at=None, event_state=None, event_error=None):
        if not finished_at:
            self.finished_at = tznow()
            self.state = OP_STATES.ERRORED
            self.save()
            return

        self.finished_at = finished_at
        if event_state == "FINISH":
            self.state = OP_STATES.FINISHED
        else:
            self.state = OP_STATES.ERRORED
            self.info = event_error
        self.save()

    class Meta:
        app_label = "chroma_core"
        unique_together = ("state", "copytool", "fid", "started_at", "finished_at")
        ordering = ["id"]


class CopytoolEvent(object):
    def _parse_type(self, type_string):
        if "ARCHIVE" in type_string:
            self.type = "ARCHIVE"
            self.state = type_string.replace("ARCHIVE_", "")
        elif "RESTORE" in type_string:
            self.type = "RESTORE"
            self.state = type_string.replace("RESTORE_", "")
        elif "REMOVE" in type_string:
            self.type = "REMOVE"
            self.state = type_string.replace("REMOVE_", "")
        elif "LOGGED_MESSAGE" == type_string:
            self.type = "LOG"
            self.state = None
        elif "REGISTER" in type_string:
            self.type = type_string
            self.state = None
        else:
            raise RuntimeError("Unknown event type: %s" % type_string)

    def __init__(self, event_time, **kwargs):
        self.timestamp = IMLDateTime.parse(event_time)
        self._parse_type(kwargs["event_type"])
        self.error = None
        self.__dict__.update(kwargs)

    def __str__(self):
        return "%s" % self.__dict__


class Copytool(StatefulObject, MeasuredEntity):
    __metaclass__ = DeletableDowncastableMetaclass

    # Fixed, minimum size (RH6.5) for HYD-3244, so that no matter what
    # ulimit -s size, and hence os.sysconf('SC_ARG_MAX') is always viable.
    HSM_ARGUMENT_MAX_SIZE_FOR_COPYTOOL = 131072  # characters

    host = models.ForeignKey("ManagedHost", related_name="copytools")
    index = models.IntegerField(
        default=0, help_text="Instance index, used to uniquely identify per-host path-filesystem-archive instances"
    )
    bin_path = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="Path to copytool binary on HSM worker node")
    archive = models.IntegerField(default=1, help_text="HSM archive number")
    filesystem = models.ForeignKey("ManagedFilesystem")
    mountpoint = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, help_text="Lustre mountpoint on HSM worker node", default="/mnt/lustre"
    )
    hsm_arguments = models.CharField(
        max_length=HSM_ARGUMENT_MAX_SIZE_FOR_COPYTOOL,
        help_text="Copytool arguments that are specific to the HSM implementation",
    )
    uuid = models.CharField(
        max_length=len("%s" % uuid.uuid4()), null=True, blank=True, help_text="UUID as assigned by cdt"
    )
    pid = models.IntegerField(null=True, blank=True, help_text="Current PID, if known")
    client_mount = models.ForeignKey("LustreClientMount", null=True, blank=True, related_name="copytools")

    states = ["unconfigured", "stopped", "started", "removed"]
    initial_state = "unconfigured"

    def __str__(self):
        return self.get_label()

    def get_label(self):
        return "%s-%s-%s-%s" % (os.path.basename(self.bin_path), self.filesystem.name, self.archive, self.index)

    def register(self, uuid):
        if self.uuid and uuid != self.uuid:
            # If this is a re-registration with a new uuid (i.e. new
            # running copytool instance, then we need to cancel all outstanding
            # actions in the UI for the old instance. The actions have
            # already been canceled on the coordinator, so this is just
            # to keep the UI in sync with reality.
            log.warn("Canceling stale operations for %s" % self)
            self.cancel_current_operations()

        self.uuid = uuid
        self.set_state("started")
        self.save()

    def unregister(self):
        self.uuid = None
        self.set_state("stopped")
        self.save()

    def create_operation(self, start_time, type, path, fid):
        try:
            return self.operations.create(
                started_at=start_time, state=OP_STATES.STARTED, type=resolve_value("type", type), path=path, fid=fid
            )
        except KeyError:
            log.error("Unknown operation type: %s" % type)

    @property
    def current_operations(self):
        return self.operations.exclude(state__in=[OP_STATES.FINISHED, OP_STATES.ERRORED])

    def cancel_current_operations(self):
        for operation in self.current_operations:
            log.warn("Canceling operation: %s" % operation)
            operation.finish()

    def get_deps(self, state=None):
        if not state:
            state = self.state

        client_mount = ObjectCache.get_one(LustreClientMount, lambda cm: cm.id == self.client_mount_id)

        deps = []
        if state == "started":
            # Depend on the client mount being mounted in order to
            # start or stay running.
            deps.append(DependOn(client_mount, "mounted", fix_state="stopped"))

        if state != "removed":
            # If the client mount is going to be removed, then the
            # copytool should also be removed.
            deps.append(
                DependOn(
                    client_mount,
                    "mounted",
                    acceptable_states=list(set(self.client_mount.states) - set(["removed"])),
                    fix_state="removed",
                )
            )

        return DependAll(deps)

    reverse_deps = {"LustreClientMount": lambda cm: ObjectCache.client_mount_copytools(cm.id)}

    class Meta:
        app_label = "chroma_core"
        unique_together = ("host", "bin_path", "filesystem", "archive", "index")
        ordering = ["id"]


class StartCopytoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Copytool, "stopped", "started")
    copytool = models.ForeignKey(Copytool)
    stateful_object = "copytool"
    state_verb = "Start"

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, copytool):
        return {"copytool_id": copytool.pk}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_copytool"]

    def description(self):
        return "Start copytool %s on worker %s" % (self.copytool, self.copytool.host)

    def get_steps(self):
        return [(StartCopytoolStep, {"host": self.copytool.host, "copytool": self.copytool})]


class StartCopytoolStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        copytool = kwargs["copytool"]

        self.invoke_agent_expect_result(host, "start_monitored_copytool", {"id": str(copytool.id)})


class StopCopytoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Copytool, "started", "stopped")
    copytool = models.ForeignKey(Copytool)
    stateful_object = "copytool"
    state_verb = "Stop"

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, copytool):
        return {"copytool_id": copytool.pk}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["stop_copytool"]

    def get_confirmation_string(self):
        return StopCopytoolJob.long_description(None)

    def get_requires_confirmation(self):
        return True

    def description(self):
        return "Stop copytool %s on worker %s" % (self.copytool, self.copytool.host)

    def get_steps(self):
        return [
            (CancelActiveOperationsStep, {"copytool": self.copytool}),
            (StopCopytoolStep, {"host": self.copytool.host, "copytool": self.copytool}),
        ]


class StopCopytoolStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        copytool = kwargs["copytool"]

        self.invoke_agent_expect_result(host, "stop_monitored_copytool", {"id": str(copytool.id)})


class ConfigureCopytoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Copytool, "unconfigured", "stopped")
    copytool = models.ForeignKey(Copytool)
    stateful_object = "copytool"
    state_verb = "Configure"

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 10

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, copytool):
        return {"copytool_id": copytool.pk}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_copytool"]

    def description(self):
        return "Configure copytool %s on worker %s" % (self.copytool, self.copytool.host)

    def get_steps(self):
        return [
            (
                ConfigureCopytoolStep,
                {
                    "host": self.copytool.host,
                    "filesystem": self.copytool.filesystem,
                    "client_mount": self.copytool.client_mount,
                    "copytool": self.copytool,
                },
            )
        ]


class ConfigureCopytoolStep(Step):
    def run(self, kwargs):
        host = kwargs["host"]
        filesystem = kwargs["filesystem"]
        client_mount = kwargs["client_mount"]
        copytool = kwargs["copytool"]

        payload = dict(
            id=str(copytool.id),
            index=copytool.index,
            bin_path=copytool.bin_path,
            archive_number=copytool.archive,
            filesystem=filesystem.name,
            mountpoint=client_mount.mountpoint,
            hsm_arguments=copytool.hsm_arguments,
        )
        self.invoke_agent(host, "configure_copytool", payload)


class RemoveCopytoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Copytool, "stopped", "removed")
    copytool = models.ForeignKey(Copytool)
    stateful_object = "copytool"
    state_verb = "Remove"

    display_group = Job.JOB_GROUPS.RARE
    display_order = 10

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, copytool):
        return {"copytool_id": copytool.pk}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["remove_copytool"]

    def get_confirmation_string(self):
        return RemoveCopytoolJob.long_description(None)

    def get_requires_confirmation(self):
        return True

    def description(self):
        return "Remove copytool %s on worker %s" % (self.copytool, self.copytool.host)

    def get_steps(self):
        return [
            (CancelActiveOperationsStep, {"copytool": self.copytool}),
            (StopCopytoolStep, {"host": self.copytool.host, "copytool": self.copytool}),
            (UnconfigureCopytoolStep, {"host": self.copytool.host, "copytool": self.copytool}),
            (DeleteCopytoolStep, {"copytool": self.copytool}),
        ]

    def get_deps(self):
        search = lambda ct: ct.host == self.copytool.host
        copytools = ObjectCache.get(Copytool, search)

        # Only force an unmount if this is the only copytool associated
        # with the host.
        if len(copytools) == 1:
            search = lambda cm: cm.id == self.copytool.client_mount_id
            client_mount = ObjectCache.get_one(LustreClientMount, search)
            return DependOn(client_mount, "unmounted")
        else:
            return DependAll()


class CancelActiveOperationsStep(Step):
    database = True

    def run(self, kwargs):
        copytool = kwargs["copytool"]

        copytool.cancel_current_operations()


class UnconfigureCopytoolStep(Step):
    def run(self, kwargs):
        host = kwargs["host"]
        copytool = kwargs["copytool"]

        self.invoke_agent(host, "unconfigure_copytool", {"id": str(copytool.id)})


class RemoveUnconfiguredCopytoolJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(Copytool, "unconfigured", "removed")
    copytool = models.ForeignKey(Copytool)
    stateful_object = "copytool"
    state_verb = "Remove"

    display_group = Job.JOB_GROUPS.RARE
    display_order = 10

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, copytool):
        return {"copytool_id": copytool.pk}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["remove_copytool"]

    def get_confirmation_string(self):
        return RemoveUnconfiguredCopytoolJob.long_description(None)

    def get_requires_confirmation(self):
        return True

    def description(self):
        return "Remove copytool %s on worker %s" % (self.copytool, self.copytool.host)

    def get_steps(self):
        return [(DeleteCopytoolStep, {"copytool": self.copytool})]

    def get_deps(self):
        search = lambda ct: ct.host == self.copytool.host
        copytools = ObjectCache.get(Copytool, search)

        # Only force an unmount if this is the only copytool associated
        # with the host.
        if len(copytools) == 1:
            search = lambda cm: cm.id == self.copytool.client_mount_id
            client_mount = ObjectCache.get_one(LustreClientMount, search)
            return DependOn(client_mount, "unmounted")
        else:
            return DependAll()


class DeleteCopytoolStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        kwargs["copytool"].mark_deleted()


class ForceRemoveCopytoolJob(AdvertisedJob):
    copytool = models.ForeignKey(Copytool)
    classes = ["Copytool"]
    verb = "Force Remove"

    requires_confirmation = True

    display_group = Job.JOB_GROUPS.LAST_RESORT
    display_order = 10

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, copytool):
        return {"copytool_id": copytool.id}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["force_remove_copytool"]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)

    def description(self):
        return "Force remove copytool %s from configuration" % self.copytool

    def get_steps(self):
        return [
            (CancelActiveOperationsStep, {"copytool": self.copytool}),
            (DeleteCopytoolStep, {"copytool": self.copytool}),
        ]
