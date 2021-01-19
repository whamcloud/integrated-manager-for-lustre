# -*- coding: utf-8 -*-
# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import threading
import random
import string
from collections import defaultdict

from django.utils.timezone import now
from django.db import models
from django.db.models import CASCADE
from toolz import dicttoolz

from chroma_core.lib.job import Step, DependAll
from chroma_core.models import corosync_common
from chroma_core.models import CorosyncConfiguration
from chroma_core.services import log_register
from chroma_core.services.job_scheduler import job_scheduler_notify

logging = log_register("corosync2")


class Corosync2Configuration(CorosyncConfiguration):
    # We want separate versions from the CorosyncConfiguration
    route_map = None
    transition_map = None
    job_class_map = None

    def __str__(self):
        return "%s Corosync2 configuration" % self.host

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_label(self):
        return "corosync2 configuration"

    reverse_deps = {"PacemakerConfiguration": lambda pc: Corosync2Configuration.objects.filter(host_id=pc.host.id)}

    # This is temporary, although will work perfectly functionally. Once landed we will move to
    #  use the sparse table functionality.
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.record_type = "Corosync2Configuration"
        return super(Corosync2Configuration, self).save(force_insert, force_update, using, update_fields)

    @property
    def configure_job_name(self):
        return "ConfigureCorosync2Job"


# Semaphore for operations so that when we configure corosync for each HA cluster we configure
# one node at a time hence removing any race conditions.
peer_mcast_ports_configuration_lock = defaultdict(lambda: threading.RLock())


class AutoConfigureCorosyncStep(Step):
    idempotent = True
    database = True
    _pcs_password_length = 20
    peer_mcast_ports = {}

    def __init__(self, job, args, log_callback, console_callback, cancel_event):
        super(AutoConfigureCorosyncStep, self).__init__(job, args, log_callback, console_callback, cancel_event)

        self._parent_console_callback = self._console_callback
        self._console_callback = self._masking_console_callback
        self._pcs_password = self._create_pcs_password()

    @classmethod
    def _corosync_peers(cls, new_fqdn, mcast_port):
        """Because the mcast_ports are deemed to be unique, in fact we work hard to make them
        unique we can say that all configured (!unconfigured) corosync configurations with the same
        mcast port and same mcast address are peers

        :param new_fqdn: str The fqdn of the new node we are looking for matching mcast ports.
        :param mcast_port: int The mcast_port to look up and by inference the mcast_port of the new_fqdn.
        :return: List of fqdns of the peers.
        """

        # Need to keep in sync with the DB so update from the DB before anything else.
        current_db_entries = {}
        for corosync_configuration in Corosync2Configuration.objects.all():
            current_db_entries[corosync_configuration.host.fqdn] = corosync_configuration.mcast_port

            if corosync_configuration.mcast_port is not None:
                cls.peer_mcast_ports[corosync_configuration.host.fqdn] = corosync_configuration.mcast_port

        # Now we need to remove any corosync configurations that have been deleted.
        for corosync_configuration in Corosync2Configuration._base_manager.filter(not_deleted=None):
            # Only remove the entries that are not currently in the db - a host may be deleted and re-added
            if corosync_configuration.host.fqdn not in current_db_entries:
                cls.peer_mcast_ports.pop(corosync_configuration.host.fqdn, None)

        # Do this at the end because this could be different from the DB if this is an update.
        cls.peer_mcast_ports[new_fqdn] = mcast_port

        # Return list of peers, but peers do not include ourselves.
        peers = [
            match_fqdn
            for match_fqdn, match_mcast_port in cls.peer_mcast_ports.items()
            if match_mcast_port == mcast_port
        ]
        peers.remove(new_fqdn)

        return peers

    def _masking_console_callback(self, subprocess_output):
        """
        We need to mask the password so it doesn't get stored anywhere. This routine simply replaces the password
        with ******'s before passing it on to the normal logger.
        :param subprocess_output: String containing the output from each subprocess
        :return: Value from parents routine
        """
        return self._parent_console_callback(
            subprocess_output.replace(self._pcs_password, "*" * self._pcs_password_length)
        )

    @classmethod
    def _create_pcs_password(cls):
        """
        Create a random password 20 characters long suitable for use as the pcs_password.
        :return: 20 character upper/lower/numeric password.
        """
        return "".join(
            random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
            for _ in range(cls._pcs_password_length)
        )

    def run(self, kwargs):
        corosync_configuration = kwargs["corosync_configuration"]

        # detect local interfaces for use in corosync 'rings', network level configuration only
        config = self.invoke_agent_expect_result(corosync_configuration.host, "get_corosync_autoconfig")

        # Select dedicated line as ring0 to carry all the traffic by default - this
        # prevents congestion on managment network
        ring0_name, ring0_config = next(
            (interface, config) for interface, config in config["interfaces"].items() if config["dedicated"] == True
        )
        ring1_name, ring1_config = next(
            (interface, config) for interface, config in config["interfaces"].items() if config["dedicated"] == False
        )

        # apply the configurations of corosync 'rings', network level configuration only
        self.invoke_agent_expect_result(
            corosync_configuration.host,
            "configure_network",
            {
                "ring0_name": ring0_name,
                "ring1_name": ring1_name,
                "ring1_ipaddr": ring1_config["ipaddr"],
                "ring1_prefix": ring1_config["prefix"],
            },
        )

        logging.debug("Node %s returned corosync configuration %s" % (corosync_configuration.host.fqdn, config))

        # Serialize across nodes with the same mcast_port so that we ensure commands
        # are executed in the same order.
        with peer_mcast_ports_configuration_lock[config["mcast_port"]]:
            from chroma_core.models import ManagedHost

            corosync_peers = self._corosync_peers(corosync_configuration.host.fqdn, config["mcast_port"])

            logging.debug(
                "Node %s has corosync peers %s" % (corosync_configuration.host.fqdn, ",".join(corosync_peers))
            )

            # If we are adding then we action on a host that is already part of the cluster
            # otherwise we have to action on the host we are adding because it is the first node in the cluster
            # TODO: Harden this up a little so it tries to pick a peer that is actively communicating, might be useful
            # when adding a new host in place of an old host. Also if ignoring peer, should we destroy that peer's
            # corosync configuration?
            actioning_host = corosync_configuration.host
            if corosync_peers:
                peer = ManagedHost.objects.get(fqdn=corosync_peers[0])
                if peer.state in ["managed", "packages_installed"]:
                    actioning_host = peer
                else:
                    logging.warning(
                        "peer corosync config ignored as host state == %s (not packages_installed or "
                        "managed)" % peer.state
                    )

            logging.debug(
                "actioning host for %s corosync configuration stage 2: %s"
                % (corosync_configuration.host.fqdn, actioning_host.fqdn)
            )

            # Stage 1 configures pcsd on the host being added, sets the password, enables and starts it etc.
            self.invoke_agent_expect_result(
                corosync_configuration.host,
                "configure_corosync2_stage_1",
                {
                    "mcast_port": config["mcast_port"],
                    "pcs_password": self._pcs_password,
                    "fqdn": corosync_configuration.host.fqdn,
                },
            )

            corosync_configuration.host.corosync_ring0 = ring0_config["ipaddr"]
            corosync_configuration.host.save(update_fields=["corosync_ring0"])

            # Stage 2 configures the cluster either by creating it or adding a node to it.
            self.invoke_agent_expect_result(
                actioning_host,
                "configure_corosync2_stage_2",
                {
                    "ring0_name": ring0_name,
                    "ring1_name": ring1_name,
                    "new_node_fqdn": corosync_configuration.host.corosync_ring0,
                    "mcast_port": config["mcast_port"],
                    "pcs_password": self._pcs_password,
                    "create_cluster": actioning_host == corosync_configuration.host,
                },
            )

            logging.debug("Node %s corosync configuration complete" % corosync_configuration.host.fqdn)

        job_scheduler_notify.notify(
            corosync_configuration,
            now(),
            {"mcast_port": config["mcast_port"], "network_interfaces": [ring0_name, ring1_name]},
        )


class AutoConfigureCorosync2Job(corosync_common.AutoConfigureCorosyncJob):
    state_transition = corosync_common.AutoConfigureCorosyncJob.StateTransition(
        Corosync2Configuration, "unconfigured", "stopped"
    )
    corosync_configuration = models.ForeignKey(Corosync2Configuration, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return [(AutoConfigureCorosyncStep, {"corosync_configuration": self.corosync_configuration})]


class UnconfigureCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        # Serialize across nodes with the same mcast_port so that we ensure commands
        # are executed in the same order.
        with peer_mcast_ports_configuration_lock[kwargs["mcast_port"]]:
            self.invoke_agent_expect_result(
                kwargs["host"],
                "unconfigure_corosync2",
                {"host_fqdn": kwargs["host"].corosync_ring0, "mcast_port": kwargs["mcast_port"]},
            )


class UnconfigureCorosync2Job(corosync_common.UnconfigureCorosyncJob):
    state_transition = corosync_common.UnconfigureCorosyncJob.StateTransition(
        Corosync2Configuration, "stopped", "unconfigured"
    )
    corosync_configuration = models.ForeignKey(Corosync2Configuration, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return [
            (
                UnconfigureCorosyncStep,
                {"host": self.corosync_configuration.host, "mcast_port": self.corosync_configuration.mcast_port},
            )
        ]


class StartCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs["host"], "start_corosync2")


class StartCorosync2Job(corosync_common.StartCorosyncJob):
    state_transition = corosync_common.StartCorosyncJob.StateTransition(Corosync2Configuration, "stopped", "started")
    corosync_configuration = models.ForeignKey(Corosync2Configuration, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return [(StartCorosyncStep, {"host": self.corosync_configuration.host})]


class StopCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs["host"], "stop_corosync2")


class StopCorosync2Job(corosync_common.StopCorosyncJob):
    state_transition = corosync_common.StopCorosyncJob.StateTransition(Corosync2Configuration, "started", "stopped")
    corosync_configuration = models.ForeignKey(Corosync2Configuration, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        return [(StopCorosyncStep, {"host": self.corosync_configuration.host})]


class ChangeMcastPortStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(
            kwargs["fqdn"],
            "change_mcast_port",
            kwargs["mcast_port"],
        )


class ActivateClusterMaintenceModeStep(Step):
    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(
            kwargs["fqdn"], "crm_attribute", ["--type", "crm_config", "--name", "maintenance-mode", "--update", "true"]
        )


class DeactivateClusterMaintenceModeStep(Step):
    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(
            kwargs["fqdn"], "crm_attribute", ["--type", "crm_config", "--name", "maintenance-mode", "--delete"]
        )


class SyncClusterStep(Step):
    def run(self, kwargs):
        self.invoke_rust_agent_expect_result(kwargs["fqdn"], "pcs", ["cluster", "sync"])


class RestartCorosync2Step(Step):
    idempotent = True

    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(kwargs["fqdn"], "restart_unit", "corosync.service")


class AddFirewallPortStep(Step):
    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(
            kwargs["fqdn"], "add_firewall_port", [kwargs["port"], kwargs["proto"]]
        )


class RemoveFirewallPortStep(Step):
    def run(self, kwargs):
        return self.invoke_rust_agent_expect_result(
            kwargs["fqdn"], "remove_firewall_port", [kwargs["port"], kwargs["proto"]]
        )


class ConfigureCorosync2Job(corosync_common.ConfigureCorosyncJob):
    corosync_configuration = models.ForeignKey(Corosync2Configuration, on_delete=CASCADE)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def get_steps(self):
        from chroma_core.models import HaCluster

        corosync_configuration = self.corosync_configuration
        host = corosync_configuration.host
        peers = HaCluster.host_peers(host)

        fqdn_kwargs = {"fqdn": host.fqdn}

        steps = [
            (ActivateClusterMaintenceModeStep, fqdn_kwargs),
            (ChangeMcastPortStep, dicttoolz.merge(fqdn_kwargs, {"mcast_port": self.mcast_port})),
            (SyncClusterStep, fqdn_kwargs),
        ]

        for h in peers:
            old_port = h.corosync_configuration.mcast_port

            if old_port is not None:
                steps += [(RemoveFirewallPortStep, {"fqdn": h.fqdn, "proto": "udp", "port": old_port})]

            steps += [(AddFirewallPortStep, {"fqdn": h.fqdn, "proto": "udp", "port": self.mcast_port})]

        steps += [(RestartCorosync2Step, {"fqdn": h.fqdn}) for h in peers]
        steps += [(DeactivateClusterMaintenceModeStep, fqdn_kwargs)]

        return steps

    def get_deps(self):
        return DependAll()

    def on_success(self):
        from chroma_core.models import HaCluster

        for h in HaCluster.host_peers(self.corosync_configuration.host):
            job_scheduler_notify.notify(h.corosync_configuration, now(), {"mcast_port": self.mcast_port})
