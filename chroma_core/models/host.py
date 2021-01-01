# -*- coding: utf-8 -*-
# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import json
import logging
import datetime

from django.db import models
from django.db import transaction
from django.db import IntegrityError
from django.db.models import CASCADE
from django.utils.timezone import now as tznow

from django.db.models.query_utils import Q

from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.influx import influx_post
from chroma_core.models.jobs import (
    StateChangeJob,
    DeletableStatefulObject,
    NullStateChangeJob,
    StateLock,
    Job,
    AdvertisedJob,
)
from chroma_core.models.alert import AlertState, AlertStateBase
from chroma_core.models.pacemaker import PacemakerConfiguration
from chroma_core.models.corosync import CorosyncConfiguration
from chroma_core.models.corosync2 import Corosync2Configuration
from chroma_core.models.ntp import (
    NTPConfiguration,
    TimeOutOfSyncAlert,
    NoTimeSyncAlert,
    UnknownTimeSyncAlert,
    MultipleTimeSyncAlert,
)
from chroma_core.models.event import AlertEvent
from chroma_core.lib.job import job_log
from chroma_core.lib.job import DependOn
from chroma_core.lib.job import DependAll
from chroma_core.lib.job import DependAny
from chroma_core.lib.job import Step
from chroma_core.models.utils import DeletableMetaclass
from chroma_core.models.utils import get_all_sub_classes
from chroma_help.help import help_text
from chroma_core.services.job_scheduler import job_scheduler_notify
from iml_common.lib.util import ExceptionThrowingThread
from chroma_core.models.sparse_model import VariantDescriptor

import settings

REPO_PATH = "/etc/yum.repos.d/"
REPO_FILENAME = "Intel-Lustre-Agent.repo"


# FIXME: HYD-1367: Chroma 1.0 Job objects aren't amenable to using m2m
# attributes for this because:
# * constructor in command_run_jobs doesn't know how to deal with them
# * assigning them requires model to be saved first, which means
#   we can't e.g. check deps before saving job
class HostListMixin(Job):
    class Meta:
        abstract = True
        app_label = "chroma_core"

    host_ids = models.CharField(max_length=512)

    def __init__(self, *args, **kwargs):
        self._cached_host_ids = "None-Cached"
        super(HostListMixin, self).__init__(*args, **kwargs)

    @property
    def hosts(self):
        if self._cached_host_ids != self.host_ids:
            if not self.host_ids:
                hosts = ManagedHost.objects.all()
            else:
                hosts = ManagedHost.objects.filter(id__in=json.loads(self.host_ids))

            self._hosts = list(hosts)
            self._cached_host_ids = self.host_ids

        return self._hosts


class ManagedHost(DeletableStatefulObject):
    address = models.CharField(max_length=255, help_text="A URI like 'user@myhost.net:22'")

    # A fully qualified domain name like flint02.testnet
    fqdn = models.CharField(max_length=255, help_text="Unicode string, fully qualified domain name")

    # a nodename to match against fqdn in corosync output
    nodename = models.CharField(max_length=255, help_text="Unicode string, node name")

    # The last known boot time
    boot_time = models.DateTimeField(null=True, blank=True)

    # Recursive relationship to keep track of cluster peers
    ha_cluster_peers = models.ManyToManyField("self", blank=True, help_text="List of peers in this host's HA cluster")

    # Profile of the server specifying some configured characteristics
    # FIXME: nullable to allow migration, but really shouldn't be
    server_profile = models.ForeignKey("ServerProfile", null=True, blank=True, on_delete=CASCADE)

    needs_update = models.BooleanField(
        default=False, help_text="True if there are package updates available for this server"
    )

    corosync_ring0 = models.CharField(
        max_length=255, help_text="Unicode string, hostname used to configure corosync ring0"
    )

    # The fields below are how the agent was installed or how it was attempted to install in the case of a failed install
    INSTALL_MANUAL = (
        "manual"  # The agent was installed manually by the user logging into the server and running a command
    )
    INSTALL_SSHPSW = (
        "id_password_root"  # The user provided a password for the server so that ssh could be used for agent install
    )
    INSTALL_SSHPKY = "private_key_choice"  # The user provided a private key with password the agent install
    INSTALL_SSHSKY = "existing_keys_choice"  # The server can be contacted via a shared key for the agent install

    # The method used to install the host
    install_method = models.CharField(max_length=32, help_text="The method used to install the agent on the server")

    states = ["undeployed", "unconfigured", "packages_installed", "managed", "monitored", "working", "removed"]
    initial_state = "unconfigured"

    class Meta:
        app_label = "chroma_core"
        unique_together = ("address",)
        ordering = ["id"]

    def __str__(self):
        return self.get_label()

    @property
    def is_worker(self):
        return self.server_profile.worker

    @property
    def is_lustre_server(self):
        return not self.server_profile.worker

    @property
    def is_managed(self):
        return self.server_profile.managed

    @property
    def is_monitored(self):
        return not self.server_profile.managed

    def get_label(self):
        """Return the FQDN if it is known, else the address"""
        name = self.fqdn

        if name.endswith(".localdomain"):
            name = name[: -len(".localdomain")]

        return name

    def save(self, *args, **kwargs):
        try:
            ManagedHost.objects.get(~Q(pk=self.pk), fqdn=self.fqdn)
            raise IntegrityError("FQDN %s in use" % self.fqdn)
        except ManagedHost.DoesNotExist:
            pass

        super(ManagedHost, self).save(*args, **kwargs)

    def get_available_states(self, begin_state):
        if begin_state == "undeployed":
            return [self.server_profile.initial_state] if self.install_method != ManagedHost.INSTALL_MANUAL else []
        elif begin_state in ["undeployed", "unconfigured"]:
            return ["removed", "packages_installed", "monitored", "managed", "working"]
        elif begin_state in ["packages_installed"]:
            return ["removed", "monitored", "managed", "working"]
        elif self.immutable_state:
            return ["removed"]
        else:
            return super(ManagedHost, self).get_available_states(begin_state)

    def _get_configuration(self, configuration_name):
        """
        We can't rely on the standard related_name functionality because it doesn't (as far as I can tell) allow us to
        return None when there is no forward reference. So for now we have to place this reference reference handles in
        that return none if there is no reference
        :return: Reference to object or None if not object.
        """
        try:
            configuration = getattr(self, "_%s_configuration" % configuration_name)
        except (PacemakerConfiguration.DoesNotExist, CorosyncConfiguration.DoesNotExist, NTPConfiguration.DoesNotExist):
            return None

        if configuration.state == "removed":
            return None
        else:
            return configuration

    @property
    def pacemaker_configuration(self):
        return self._get_configuration("pacemaker")

    @property
    def corosync_configuration(self):
        return self._get_configuration("corosync")

    @property
    def ntp_configuration(self):
        return self._get_configuration("ntp")


class Volume(models.Model):
    storage_resource = models.ForeignKey("StorageResourceRecord", blank=True, null=True, on_delete=models.PROTECT)

    # Size may be null for VolumeNodes created when setting up
    # from a JSON file which just tells us a path.
    size = models.BigIntegerField(
        blank=True,
        null=True,
        help_text="Integer number of bytes. "
        "Can be null if this device "
        "was manually created, rather "
        "than detected.",
    )

    label = models.CharField(max_length=128)

    filesystem_type = models.CharField(max_length=32, blank=True, null=True)

    usable_for_lustre = models.BooleanField(
        default=True, help_text="True if the Volume can be selected for use as a new Lustre Target"
    )

    __metaclass__ = DeletableMetaclass

    class Meta:
        unique_together = ("storage_resource",)
        app_label = "chroma_core"
        ordering = ["id"]

    def get_kind(self):
        if not hasattr(self, "kind"):
            self.kind = self._get_kind()

        return self.kind

    def _get_kind(self):
        """:return: A string or unicode string which is a human readable noun corresponding
        to the class of storage e.g. LVM LV, Linux partition, iSCSI LUN"""
        if not self.storage_resource:
            return "Unknown"

        resource_klass = self.storage_resource.to_resource_class()
        return resource_klass._meta.label

    def _get_label(self):
        if not self.storage_resource_id:
            if self.label:
                return self.label
            else:
                if self.volumenode_set.count():
                    volumenode = self.volumenode_set.all()[0]
                    return "%s:%s" % (volumenode.host, volumenode.path)
                else:
                    return ""

        # TODO: this is a link to the local e.g. ScsiDevice resource: to get the
        # best possible name, we should follow back to VirtualDisk ancestors, and
        # if there is only one VirtualDisk in the ancestry then use its name

        return self.storage_resource.alias_or_name()

    def save(self, *args, **kwargs):
        self.label = self._get_label()
        self.kind = self._get_kind()
        super(Volume, self).save(*args, **kwargs)

    @staticmethod
    def ha_status_label(volumenode_count, primary_count, failover_count):
        if volumenode_count == 1 and primary_count == 0:
            return "configured-noha"
        elif volumenode_count == 1 and primary_count > 0:
            return "configured-noha"
        elif primary_count > 0 and failover_count == 0:
            return "configured-noha"
        elif primary_count > 0 and failover_count > 0:
            return "configured-ha"
        else:
            # Has no VolumeNodes, or has >1 but no primary
            return "unconfigured"


class VolumeNode(models.Model):
    volume = models.ForeignKey(Volume, on_delete=CASCADE)
    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)
    path = models.CharField(max_length=512, help_text="Device node path, e.g. '/dev/sda/'")

    __metaclass__ = DeletableMetaclass

    storage_resource = models.ForeignKey("StorageResourceRecord", blank=True, null=True, on_delete=CASCADE)

    primary = models.BooleanField(
        default=False,
        help_text="If ``true``, this node will\
            be used for the primary Lustre server when creating a target",
    )

    use = models.BooleanField(
        default=True,
        help_text="If ``true``, this node will \
            be used as a Lustre server when creating a target (if primary is not set,\
            this node will be used as a secondary server)",
    )

    class Meta:
        unique_together = ("host", "path")
        app_label = "chroma_core"
        ordering = ["id"]

    def __str__(self):
        return "%s:%s" % (self.host, self.path)


class RemoveServerConfStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        self.invoke_agent(host, "deregister_server")


class LearnDevicesStep(Step):
    idempotent = True

    # Require database to talk to storage_plugin_manager
    database = True

    def run(self, kwargs):
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        # Get the device-scan output
        host = kwargs["host"]

        plugin_data = {}
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        for plugin in storage_plugin_manager.loaded_plugin_names:
            try:
                plugin_data[plugin] = self.invoke_agent(host, "device_plugin", {"plugin": plugin})[plugin]
            except AgentException:
                self.log("No data for plugin %s from host %s" % (plugin, host))

        AgentDaemonRpcInterface().setup_host(host.id, plugin_data)


class TriggerPluginUpdatesStep(Step):
    idempotent = True

    def trigger_plugin_updates(self, host, plugin_names):
        self.invoke_agent_expect_result(host, "trigger_plugin_update", {"plugin_names": plugin_names})

    def run(self, kwargs):
        threads = []

        for host in kwargs["hosts"]:
            thread = ExceptionThrowingThread(target=self.trigger_plugin_updates, args=(host, kwargs["plugin_names"]))
            thread.start()
            threads.append(thread)

        ExceptionThrowingThread.wait_for_threads(
            threads
        )  # This will raise an exception if any of the threads raise an exception


class DeployStep(Step):
    # TODO: This timeout is the time to wait for the agent to successfully connect back to the manager. It is stupidly long
    # because we have seen the agent take stupidly long times to connect back to the manager. I've raised HYD-4769
    # to address the need for this long time out.
    DEPLOY_STARTUP_TIMEOUT = 360

    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentSsh
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        host = kwargs["host"]

        # TODO: before kicking this off, check if an existing agent install is present:
        # the decision to clear it out/reset it should be something explicit maybe
        # even requiring user permission
        agent_ssh = AgentSsh(host.fqdn)
        auth_args = agent_ssh.construct_ssh_auth_args(
            kwargs["__auth_args"]["root_pw"], kwargs["__auth_args"]["pkey"], kwargs["__auth_args"]["pkey_pw"]
        )

        rc, stdout, stderr = agent_ssh.ssh(
            "curl -k %s/agent/setup/%s/%s | python"
            % (settings.SERVER_HTTP_URL, kwargs["token"].secret, "?profile_name=%s" % kwargs["profile_name"]),
            auth_args=auth_args,
        )

        if rc == 0:
            try:
                json.loads(stdout)
            except ValueError:
                # Not valid JSON
                raise AgentException(
                    host.fqdn,
                    "DeployAgent",
                    kwargs,
                    help_text["deploy_failed_to_register_host"] % (host.fqdn, rc, stdout, stderr),
                )
        else:
            raise AgentException(
                host.fqdn,
                "DeployAgent",
                kwargs,
                help_text["deploy_failed_to_register_host"] % (host.fqdn, rc, stdout, stderr),
            )

        # Now wait for the agent to actually connect back to the manager.
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        if not AgentRpc.await_session(host.fqdn, self.DEPLOY_STARTUP_TIMEOUT):
            raise AgentException(
                host.fqdn, "DeployAgent", kwargs, help_text["deployed_agent_failed_to_contact_manager"] % host.fqdn
            )


class AwaitRebootStep(Step):
    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        old_rust_session_id = self.invoke_rust_local_action_expect_result("get_session", kwargs["host"].fqdn)
        self.invoke_rust_local_action_expect_result(
            "await_next_session", (kwargs["host"].fqdn, old_rust_session_id, kwargs["timeout"])
        )

        AgentRpc.await_restart(kwargs["host"].fqdn, kwargs["timeout"])


class DeployHostJob(StateChangeJob):
    """Handles Deployment of the IML agent code base to a new host"""

    state_transition = StateChangeJob.StateTransition(ManagedHost, "undeployed", "unconfigured")
    stateful_object = "managed_host"
    managed_host = models.ForeignKey(ManagedHost, on_delete=CASCADE)
    state_verb = "Deploy agent"
    auth_args = {}

    # Not cancellable because uses SSH rather than usual agent comms
    cancellable = False

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    def __init__(self, *args, **kwargs):
        super(DeployHostJob, self).__init__(*args, **kwargs)

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["deploy_agent"]

    def description(self):
        return "Deploying agent to %s" % self.managed_host.address

    def get_steps(self):
        from chroma_core.models.registration_token import RegistrationToken

        # Commit token so that registration request handler will see it
        with transaction.atomic():
            token = RegistrationToken.objects.create(credits=1, profile=self.managed_host.server_profile)

        return [
            (
                DeployStep,
                {
                    "token": token,
                    "host": self.managed_host,
                    "profile_name": self.managed_host.server_profile.name,
                    "__auth_args": self.auth_args,
                },
            )
        ]

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class RebootIfNeededStep(Step):
    def _reboot_needed(self, host):
        # Check if we are running the required (lustre) kernel
        kernel_status = self.invoke_agent(host, "kernel_status")
        selinux_status = self.invoke_agent(host, "selinux_status")

        reboot_needed = (selinux_status["status"] != "Disabled") or (
            kernel_status["running"] != kernel_status["required"]
            and kernel_status["required"]
            and kernel_status["required"] in kernel_status["available"]
        )
        if reboot_needed:
            self.log(
                "Reboot of %s required to switch from running kernel %s to required %s"
                % (host, kernel_status["running"], kernel_status["required"])
            )

        return reboot_needed

    def run(self, kwargs):
        host = kwargs["host"]

        if host.is_managed and self._reboot_needed(host):
            old_rust_session_id = self.invoke_rust_local_action_expect_result("get_session", host.fqdn)

            self.invoke_agent(host, "reboot_server")

            from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

            AgentRpc.await_restart(host.fqdn, kwargs["timeout"])
            self.invoke_rust_local_action_expect_result(
                "await_next_session", (host.fqdn, old_rust_session_id, kwargs["timeout"])
            )


class InstallPackagesStep(Step):
    # Require database because we update package records
    database = True

    @classmethod
    def describe(cls, kwargs):
        return "Installing packages on %s" % kwargs["host"]

    def run(self, kwargs):
        host = kwargs["host"]

        self.invoke_agent_expect_result(
            host, "install_packages", {"repos": kwargs["enablerepos"], "packages": kwargs["packages"]}
        )

        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc, LocalActionException

        old_session_id = AgentRpc.get_session_id(host.fqdn)

        try:
            old_rust_session_id = self.invoke_rust_local_action_expect_result("get_session", host.fqdn)
        except LocalActionException:
            old_rust_session_id = None

        # If we have installed any updates at all, then assume it is necessary to restart the agent, as
        # they could be things the agent uses/imports or API changes, specifically to kernel_status() below
        self.invoke_agent(host, "restart_agent")

        AgentRpc.await_restart(host.fqdn, timeout=settings.AGENT_RESTART_TIMEOUT, old_session_id=old_session_id)

        if old_rust_session_id:
            self.invoke_rust_local_action_expect_result(
                "await_next_session", (host.fqdn, old_rust_session_id, settings.AGENT_RESTART_TIMEOUT)
            )


class InstallHostPackagesJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(ManagedHost, "unconfigured", "packages_installed")
    stateful_object = "managed_host"
    managed_host = models.ForeignKey(ManagedHost, on_delete=CASCADE)
    state_verb = help_text["continue_server_configuration"]

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 20

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["install_packages_on_host_long"]

    def description(self):
        return help_text["install_packages_on_host"] % self.managed_host

    def get_steps(self):
        """
        This is a workaround for the fact that the object for a stateful object is not updated before the job runs, it
        is a snapshot of the object when the job was requested. This seems wrong to me and something that I will endeavour
        to understand and put right. Couple with that is the fact that strangely John took a reference to the object at
        creation time meaning that is the Stateful object was re-read the reference _so_cache is invalid.

        What is really needed is self._managed_host.refresh() which updates the values in managed_host without creating
        a new managed host instance. For today this works and I will think about this an improve it for 3.0
        """
        self._so_cache = self.managed_host = ObjectCache.update(self.managed_host)

        steps = [(SetHostProfileStep, {"host": self.managed_host, "server_profile": self.managed_host.server_profile})]

        if self.managed_host.is_lustre_server:
            steps.append((LearnDevicesStep, {"host": self.managed_host}))

        steps.extend(
            [
                (
                    UpdateYumFileStep,
                    {
                        "host": self.managed_host,
                        "filename": REPO_FILENAME,
                        "file_contents": self.managed_host.server_profile.repo_contents,
                    },
                ),
                (
                    InstallPackagesStep,
                    {
                        "enablerepos": [],
                        "host": self.managed_host,
                        "packages": list(self.managed_host.server_profile.packages),
                    },
                ),
                (RebootIfNeededStep, {"host": self.managed_host, "timeout": settings.INSTALLATION_REBOOT_TIMEOUT}),
            ]
        )

        return steps

    @classmethod
    def can_run(cls, host):
        return host.state == "unconfigured"


class BaseSetupHostJob(NullStateChangeJob):
    target_object = models.ForeignKey(ManagedHost, on_delete=CASCADE)

    class Meta:
        abstract = True

    def _common_deps(self, lnet_state_required, lnet_acceptable_states, lnet_unacceptable_states):
        # It really does not feel right that this is in here, but it does sort of work. These are the things
        # it is dependent on so create them. Also I can't work out with today's state machine anywhere else to
        # put them that works.
        if self.target_object.pacemaker_configuration is None and self.target_object.server_profile.pacemaker:
            pacemaker_configuration, _ = PacemakerConfiguration.objects.get_or_create(host=self.target_object)
            ObjectCache.add(PacemakerConfiguration, pacemaker_configuration)

        if self.target_object.corosync_configuration is None and (
            self.target_object.server_profile.corosync or self.target_object.server_profile.corosync2
        ):
            if self.target_object.server_profile.corosync:
                corosync_configuration, _ = CorosyncConfiguration.objects.get_or_create(host=self.target_object)
            elif self.target_object.server_profile.corosync2:
                corosync_configuration, _ = Corosync2Configuration.objects.get_or_create(host=self.target_object)
            else:
                assert RuntimeError(
                    "Unknown corosync type for host %s profile %s"
                    % (self.target_object, self.target_object.server_profile.name)
                )

            ObjectCache.add(type(corosync_configuration), corosync_configuration)

        if self.target_object.ntp_configuration is None and self.target_object.server_profile.ntp:
            ntp_configuration, _ = NTPConfiguration.objects.get_or_create(host=self.target_object)
            ObjectCache.add(NTPConfiguration, ntp_configuration)

        deps = []

        if self.target_object.lnet_configuration:
            deps.append(
                DependOn(
                    self.target_object.lnet_configuration,
                    lnet_state_required,
                    lnet_acceptable_states,
                    lnet_unacceptable_states,
                )
            )

        if self.target_object.pacemaker_configuration:
            deps.append(DependOn(self.target_object.pacemaker_configuration, "started"))

        if self.target_object.ntp_configuration:
            deps.append(DependOn(self.target_object.ntp_configuration, "configured"))

        return DependAll(deps)


class InitialiseBlockDeviceDriversStep(Step):
    """ Perform driver initialisation routine for each block device type on a given host """

    def run(self, kwargs):
        host = kwargs["host"]

        self.invoke_agent_expect_result(host, "initialise_block_device_drivers", {})


class SetupHostJob(BaseSetupHostJob):
    """For historical reasons this is called the original name of SetupHostJob rather than the more
    obvious SetupManagedHostJob.
    """

    state_transition = StateChangeJob.StateTransition(ManagedHost, "packages_installed", "managed")
    _long_description = help_text["setup_managed_host"]
    state_verb = "Setup managed server"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def description(self):
        return help_text["setup_managed_host_on"] % self.target_object

    def get_deps(self):
        return self._common_deps("lnet_up", None, None)

    def get_steps(self):
        return [(InitialiseBlockDeviceDriversStep, {"host": self.target_object})]

    @classmethod
    def can_run(cls, host):
        return host.is_managed and not host.is_worker and (host.state != "unconfigured")


class SetupMonitoredHostJob(BaseSetupHostJob):
    state_transition = StateChangeJob.StateTransition(ManagedHost, "packages_installed", "monitored")
    _long_description = help_text["setup_monitored_host"]
    state_verb = "Setup monitored server"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_deps(self):
        # Moving out of unconfigured into lnet_unloaded will mean that lnet will start monitoring and responding to
        # the state. Once we start monitoring any state other than unconfigured is acceptable.
        return self._common_deps("lnet_unloaded", None, ["unconfigured"])

    def description(self):
        return help_text["setup_monitored_host_on"] % self.target_object

    @classmethod
    def can_run(cls, host):
        return host.is_monitored and (host.state != "unconfigured")


class SetupWorkerJob(BaseSetupHostJob):
    state_transition = StateChangeJob.StateTransition(ManagedHost, "packages_installed", "working")
    _long_description = help_text["setup_worker_host"]
    state_verb = "Setup worker node"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_deps(self):
        return self._common_deps("lnet_up", None, None)

    def description(self):
        return help_text["setup_worker_host_on"] % self.target_object

    @classmethod
    def can_run(cls, host):
        return host.is_managed and host.is_worker and (host.state != "unconfigured")


class DetectTargetsJob(HostListMixin):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["detect_targets"]

    def description(self):
        return "Scan for Lustre targets"

    def get_steps(self):
        pass


class SetHostProfileStep(Step):
    database = True

    def is_dempotent(self):
        return True

    def run(self, kwargs):
        host = kwargs["host"]
        server_profile = kwargs["server_profile"]

        self.invoke_agent_expect_result(host, "update_profile", {"profile": server_profile.as_dict})

        job_scheduler_notify.notify(host, tznow(), {"server_profile_id": server_profile.id})

        job_scheduler_notify.notify(host, tznow(), {"immutable_state": not server_profile.managed})

    @classmethod
    def describe(cls, kwargs):
        return help_text["set_host_profile_on"] % kwargs["host"]


class TriggerPluginUpdatesJob(HostListMixin):
    plugin_names_json = models.CharField(max_length=512)

    @property
    def plugin_names(self):
        return json.loads(self.plugin_names_json)

    @classmethod
    def long_description(cls, stateful_object):
        return stateful_object.description()

    def description(self):
        return help_text["Trigger plugin poll for %s plugins"] % (
            ", ".join(self.plugin_names) if self.plugin_names else "all"
        )

    def get_steps(self):
        return [(TriggerPluginUpdatesStep, {"hosts": self.hosts, "plugin_names": self.plugin_names})]

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class DeleteHostStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        from chroma_core.services.http_agent import HttpAgentRpc
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        host = kwargs["host"]
        # First, cut off any more incoming connections
        # TODO: populate a CRL and send a nginx HUP signal to reread it

        # Delete anything that is dependent on us.
        for object in host.get_dependent_objects(inclusive=True):
            # We are allowed to modify state directly because we have locked these objects
            job_log.info("Deleting dependent %s for host %s" % (object, host))
            object.cancel_current_operations()
            object.set_state("removed")
            object.mark_deleted()
            object.save()

        # Third, terminate any currently open connections and ensure there is nothing in a queue
        # which will be drained into AMQP
        HttpAgentRpc().remove_host(host.fqdn)

        # Third, for all receivers of AMQP messages from originating from hosts, ask them to
        # drain their queues, discarding any messages from the host being removed
        # ... or if we could get a bit of info from rabbitmq we could look at how many N messages
        # are pending in a queue, then track its 'messages consumed' count (if such a count exists)
        # until N + 1 messages have been consumed
        # TODO
        # The last receiver of AMQP messages to clean up is myself (JobScheduler, inside which
        # this code will execute)
        AgentRpc.remove(host.fqdn)

        # Lower all alerts associated with the host being removed
        for c in get_all_sub_classes(AlertStateBase):
            c.notify(host, False)

        # Lower any time sync alerts for the host
        TimeOutOfSyncAlert.notify(host, False)
        MultipleTimeSyncAlert.notify(host, False)
        NoTimeSyncAlert.notify(host, False)
        UnknownTimeSyncAlert.notify(host, False)

        from chroma_core.models import StorageResourceRecord
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface

        try:
            AgentDaemonRpcInterface().remove_host_resources(host.id)
        except StorageResourceRecord.DoesNotExist:
            # This is allowed, to account for the case where we submit the request_remove_resource,
            # then crash, then get restarted.
            pass

        # Remove associated lustre mounts
        for mount in host.client_mounts.all():
            mount.mark_deleted()

        # Remove configuration objects.
        for configuration in [host.pacemaker_configuration, host.corosync_configuration, host.ntp_configuration]:
            if configuration:
                configuration.set_state("removed")
                configuration.mark_deleted()
                configuration.save()

        # Mark the host itself deleted
        host.mark_deleted()
        if kwargs["force"]:
            host.state = "removed"

        # Cleanup any corosync leftovers
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM corosync_cluster c
                USING corosync_node_managed_host nh
                WHERE nh.host_id = %s
                AND cluster_id = c.id
                """,
                [host.id],
            )
            cursor.execute(
                """
                DELETE FROM lnet
                WHERE host_id = %s
                """,
                [host.id],
            )
            cursor.execute(
                """
                DELETE FROM nid
                WHERE host_id = %s
                """,
                [host.id],
            )
            cursor.execute(
                """
                DELETE FROM network_interface
                WHERE host_id = %s
                """,
                [host.id],
            )

            influx_post(settings.INFLUXDB_IML_STATS_DB, "DELETE FROM /.*net/ WHERE \"host_id\"='{}'".format(host.id))
            influx_post(settings.INFLUXDB_IML_STATS_DB, "DELETE FROM /.*lnet/ WHERE \"host\"='{}'".format(host.fqdn))
            influx_post(settings.INFLUXDB_IML_STATS_DB, "DELETE FROM /.*host/ WHERE \"host\"='{}'".format(host.fqdn))
            influx_post(settings.INFLUXDB_IML_STATS_DB, "DELETE FROM /.*target/ WHERE \"host\"='{}'".format(host.fqdn))


class CommonRemoveHostJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(None, None, None)
    stateful_object = "host"
    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)
    state_verb = "Remove"

    requires_confirmation = True

    display_group = Job.JOB_GROUPS.EMERGENCY
    display_order = 120

    class Meta:
        abstract = True

    def get_confirmation_string(self):
        return self.long_description(self.host)

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_deps(self):
        deps = []

        if self.host.lnet_configuration:
            deps.append(DependOn(self.host.lnet_configuration, "unconfigured"))

        if self.host.corosync_configuration:
            deps.append(DependOn(self.host.corosync_configuration, "unconfigured"))

        if self.host.ntp_configuration:
            deps.append(DependOn(self.host.ntp_configuration, "unconfigured"))

        return DependAll(deps)

    def get_steps(self):
        return [(RemoveServerConfStep, {"host": self.host}), (DeleteHostStep, {"host": self.host, "force": False})]


class RemoveHostJob(CommonRemoveHostJob):
    state_transition = StateChangeJob.StateTransition(ManagedHost, ["unconfigured", "monitored"], "removed")

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, host):
        return help_text["remove_monitored_configured_server"]


class RemoveManagedHostJob(CommonRemoveHostJob):
    state_transition = StateChangeJob.StateTransition(ManagedHost, ["managed", "working"], "removed")

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, host):
        return help_text["remove_configured_server"]


class ForceRemoveHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)

    requires_confirmation = True

    classes = ["ManagedHost"]

    verb = "Force Remove"

    display_group = Job.JOB_GROUPS.LAST_RESORT
    display_order = 140

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["force_remove"]

    def create_locks(self):
        locks = super(ForceRemoveHostJob, self).create_locks()

        locks.append(StateLock(job=self, locked_item=self.host, begin_state=None, end_state="removed", write=True))

        # Take a write lock on get_stateful_object if this is a StateChangeJob
        for object in self.host.get_dependent_objects(inclusive=True):
            job_log.debug("Creating StateLock on %s/%s" % (object.__class__, object.id))
            locks.append(StateLock(job=self, locked_item=object, begin_state=None, end_state="removed", write=True))

        return locks

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    def description(self):
        return "Force remove host %s from configuration" % self.host

    def get_deps(self):
        return DependAny(
            [
                DependOn(self.host, "managed", acceptable_states=self.host.not_state("removed")),
                DependOn(self.host, "monitored", acceptable_states=self.host.not_state("removed")),
                DependOn(self.host, "working", acceptable_states=self.host.not_state("removed")),
            ]
        )

    def get_steps(self):
        return [(DeleteHostStep, {"host": self.host, "force": True})]

    @classmethod
    def get_confirmation(cls, instance):
        return """WARNING This command is destructive. This command should only be performed
when the Remove command has been unsuccessful. This command will remove this server from the
Integrated Manager for Lustre configuration, but Integrated Manager for Lustre software will not be removed
from this server.  All targets that depend on this server will also be removed without any attempt to
unconfigure them. To completely remove the Integrated Manager for Lustre software from this server
(allowing it to be added to another Lustre file system) you must first contact technical support.
You should only perform this command if this server is permanently unavailable, or has never been
successfully deployed using Integrated Manager for Lustre software."""


class RebootHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)

    requires_confirmation = True

    classes = ["ManagedHost"]

    verb = "Reboot"

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 50

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["reboot_host"]

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    @classmethod
    def can_run(cls, host):
        return (
            host.is_managed
            and host.state not in ["removed", "undeployed", "unconfigured"]
            and not AlertState.filter_by_item(host)
            .filter(active=True, alert_type__in=[HostOfflineAlert.__name__, HostContactAlert.__name__])
            .exists()
        )

    def description(self):
        return "Initiate a reboot on host %s" % self.host

    def get_steps(self):
        return [(RebootHostStep, {"host": self.host})]

    @classmethod
    def get_confirmation(cls, stateful_object):
        cls.long_description(stateful_object)


class RebootHostStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        self.invoke_agent(host, "reboot_server")

        self.log("Rebooted host %s" % host)


class ShutdownHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)

    requires_confirmation = True

    classes = ["ManagedHost"]

    verb = "Shutdown"

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 60

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["shutdown_host"]

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    @classmethod
    def can_run(cls, host):
        return (
            host.is_managed
            and host.state not in ["removed", "undeployed", "unconfigured"]
            and not AlertState.filter_by_item(host)
            .filter(active=True, alert_type__in=[HostOfflineAlert.__name__, HostContactAlert.__name__])
            .exists()
        )

    def description(self):
        return "Initiate an orderly shutdown on host %s" % self.host

    def get_steps(self):
        return [(ShutdownHostStep, {"host": self.host})]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)


class ShutdownHostStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs["host"]
        self.invoke_agent(host, "shutdown_server")

        self.log("Shut down host %s" % host)


class RemoveUnconfiguredHostJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(ManagedHost, "unconfigured", "removed")
    stateful_object = "host"
    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)
    state_verb = "Remove"

    requires_confirmation = True

    display_group = Job.JOB_GROUPS.EMERGENCY
    display_order = 130

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["remove_unconfigured_server"]

    def get_confirmation_string(self):
        return RemoveUnconfiguredHostJob.long_description(None)

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        return [(DeleteHostStep, {"host": self.host, "force": False})]


class UpdatePackagesStep(RebootIfNeededStep):
    # REMEMBER: This runs against the old agent and so any API changes need to be compatible with
    # all agents that we might want to upgrade from. Forget this at your peril.
    # Require database because we update package records
    database = True

    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc, LocalActionException

        host = kwargs["host"]

        # install_packages will add any packages not existing that are specified within the profile
        # as well as upgrading/downgrading packages to the version specified
        self.invoke_agent_expect_result(
            host, "install_packages", {"repos": kwargs["enablerepos"], "packages": kwargs["packages"]}
        )

        old_session_id = AgentRpc.get_session_id(host.fqdn)

        try:
            old_rust_session_id = self.invoke_rust_local_action_expect_result("get_session", host.fqdn)
        except LocalActionException as e:
            self.log("Error finding session: {}".format(e))

            # Assume if this call fails we are dealing with pre-rust agent
            old_rust_session_id = None

        # If we have installed any updates at all, then assume it is necessary to restart the agent, as
        # they could be things the agent uses/imports or API changes, specifically to kernel_status() below
        self.invoke_agent(host, "restart_agent")

        AgentRpc.await_restart(
            kwargs["host"].fqdn, timeout=settings.AGENT_RESTART_TIMEOUT, old_session_id=old_session_id
        )

        if old_rust_session_id:
            self.invoke_rust_local_action_expect_result(
                "await_next_session", (host.fqdn, old_rust_session_id, settings.AGENT_RESTART_TIMEOUT)
            )

        # Now do some managed things
        if host.is_managed and host.pacemaker_configuration:
            # Upgrade of pacemaker packages could have left it disabled
            self.invoke_agent(kwargs["host"], "enable_pacemaker")
            # and not running,
            self.invoke_agent(kwargs["host"], "start_pacemaker")


class UpdateProfileStep(RebootIfNeededStep):
    """
    Update profile definition on node.
    """

    database = True

    def run(self, kwargs):
        self.invoke_agent(kwargs["host"], "set_profile", {"profile_json": json.dumps(kwargs["profile"].as_dict)})


class UpdateYumFileStep(RebootIfNeededStep):
    def run(self, kwargs):
        self.invoke_agent_expect_result(
            kwargs["host"], "configure_repo", {"filename": kwargs["filename"], "file_contents": kwargs["file_contents"]}
        )


class RemovePackagesStep(Step):
    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs["host"], "remove_packages", {"packages": kwargs["packages"]})


class UpdateYumFileJob(Job):
    host = models.ForeignKey(ManagedHost, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"

    @classmethod
    def long_description(cls, stateful_object):
        return "Update Agent repo file on {}".format(stateful_object.host.fqdn)

    def description(self):
        return "Update Agent Repo file on {}".format(self.host.fqdn)

    def get_steps(self):
        # the minimum repos needed on a storage server now
        repo_file_contents = self.host.server_profile.repo_contents

        return [
            (UpdateYumFileStep, {"host": self.host, "filename": REPO_FILENAME, "file_contents": repo_file_contents})
        ]


class ResetConfParamsStep(Step):
    database = True

    def run(self, args):
        # Reset version to zero so that next time the target is started
        # it will write all its parameters from chroma to lustre.
        mgt = args["mgt"]
        mgt.conf_param_version_applied = 0
        mgt.save()


class HostContactAlert(AlertStateBase):
    # This is worse than INFO because it *could* indicate that
    # a filesystem is unavailable, but it is not necessarily
    # so:
    # * Host can lose contact with us but still be servicing clients
    # * Host can be offline entirely but filesystem remains available
    #   if failover servers are available.
    default_severity = logging.WARNING

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def alert_message(self):
        return "Lost contact with host %s" % self.alert_item

    def affected_targets(self, affect_target):
        from chroma_core.models.target import get_host_targets

        ts = get_host_targets(self.alert_item.id)
        for t in ts:
            affect_target(t)

    def end_event(self):
        return AlertEvent(
            message_str="Re-established contact with host %s" % self.alert_item,
            alert_item=self.alert_item,
            alert=self,
            severity=logging.INFO,
        )


class HostOfflineAlert(AlertStateBase):
    """Alert should be raised when a Host is known to be down.

    When a corosync agent reports a peer is down in a cluster, the corresponding
    service will save a HostOfflineAlert.
    """

    # This is worse than INFO because it *could* indicate that
    # a filesystem is unavailable, but it is not necessarily
    # so:
    # * Host can be offline but filesystem remains available
    #   if failover servers are available.
    default_severity = logging.WARNING

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def alert_message(self):
        return "Host is offline %s" % self.alert_item

    def end_event(self):
        return AlertEvent(
            message_str="Host is back online %s" % self.alert_item,
            alert_item=self.alert_item,
            alert=self,
            severity=logging.INFO,
        )


class HostRebootEvent(AlertStateBase):
    variant_fields = [
        VariantDescriptor(
            "boot_time",
            datetime.datetime,
            lambda self_: datetime.datetime.strptime(self_.get_variant("boot_time", None, str), "%Y-%m-%d %H:%M:%S:%f"),
            lambda self_, value: self_.set_variant("boot_time", str, value.strftime("%Y-%m-%d %H:%M:%S:%f")),
            None,
        )
    ]

    class Meta:
        app_label = "chroma_core"
        proxy = True

    @staticmethod
    def type_name():
        return "Autodetection"

    def alert_message(self):
        return "%s restarted at %s" % (self.alert_item, self.begin)


class NoNidsPresent(Exception):
    pass


class CreateSnapshotJob(Job):
    fqdn = models.CharField(max_length=256, help_text="MGS host to create the snapshot on")
    fsname = models.CharField(max_length=8, help_text="Lustre filesystem name")
    name = models.CharField(max_length=64, help_text="Snapshot to create")
    comment = models.CharField(max_length=1024, null=True, help_text="Optional comment for the snapshot")
    use_barrier = models.BooleanField(
        default=False, help_text="Set write barrier before creating snapshot. The default value is False"
    )

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["create_snapshot"]

    def description(self):
        return "Create snapshot '{}' on '{}'".format(self.name, self.fsname)

    def get_steps(self):
        args = {"host": self.fqdn, "fsname": self.fsname, "name": self.name, "use_barrier": self.use_barrier}

        if self.comment:
            args["comment"] = self.comment

        return [(CreateSnapshotStep, args)]

    def get_deps(self):
        # To prevent circular imports
        from chroma_core.models.filesystem import ManagedFilesystem

        return DependOn(ManagedFilesystem.objects.get(name=self.fsname), "available")

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class CreateSnapshotStep(Step):
    def run(self, kwargs):
        args = {"fsname": kwargs["fsname"], "name": kwargs["name"], "use_barrier": kwargs["use_barrier"]}

        if "comment" in kwargs:
            args["comment"] = kwargs["comment"]

        self.invoke_rust_agent_expect_result(
            kwargs["host"],
            "snapshot_create",
            args,
        )


class DestroySnapshotJob(Job):
    fqdn = models.CharField(max_length=256, help_text="MGS host to destroy the snapshot on")
    fsname = models.CharField(max_length=8, help_text="Lustre filesystem name")
    name = models.CharField(max_length=64, help_text="Snapshot to destroy")
    force = models.BooleanField(default=False, help_text="Destroy the snapshot with force")

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["destroy_snapshot"]

    def description(self):
        return "Destroy snapshot '{}' of '{}'".format(self.name, self.fsname)

    def get_steps(self):
        args = {"host": self.fqdn, "fsname": self.fsname, "name": self.name, "force": self.force}
        return [(DestroySnapshotStep, args)]

    def get_deps(self):
        # To prevent circular imports
        from chroma_core.models.filesystem import ManagedFilesystem

        return DependOn(ManagedFilesystem.objects.get(name=self.fsname), "available")

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class DestroySnapshotStep(Step):
    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(
            kwargs["host"],
            "snapshot_destroy",
            {"fsname": kwargs["fsname"], "name": kwargs["name"], "force": kwargs["force"]},
        )


class MountSnapshotStep(Step):
    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(
            kwargs["host"], "snapshot_mount", {"fsname": kwargs["fsname"], "name": kwargs["name"]}
        )


class UnmountSnapshotStep(Step):
    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(
            kwargs["host"], "snapshot_unmount", {"fsname": kwargs["fsname"], "name": kwargs["name"]}
        )


class MountSnapshotJob(Job):
    fqdn = models.CharField(max_length=256)
    fsname = models.CharField(max_length=8)
    name = models.CharField(max_length=512)

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["mount_snapshot"]

    def description(self):
        return "Mount snapshot on host %s" % self.fqdn

    def get_deps(self):
        # To prevent circular imports
        from chroma_core.models.filesystem import ManagedFilesystem

        return DependOn(ManagedFilesystem.objects.get(name=self.fsname), "available")

    def get_steps(self):
        steps = [(MountSnapshotStep, {"host": self.fqdn, "fsname": self.fsname, "name": self.name})]

        return steps

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]


class UnmountSnapshotJob(Job):
    fqdn = models.CharField(max_length=256)
    fsname = models.CharField(max_length=8)
    name = models.CharField(max_length=512)

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unmount_snapshot"]

    def description(self):
        return "Unmount snapshot on host %s" % self.fqdn

    def get_deps(self):
        # To prevent circular imports
        from chroma_core.models.filesystem import ManagedFilesystem

        return DependOn(ManagedFilesystem.objects.get(name=self.fsname), "available")

    def get_steps(self):
        steps = [(UnmountSnapshotStep, {"host": self.fqdn, "fsname": self.fsname, "name": self.name})]

        return steps

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]
