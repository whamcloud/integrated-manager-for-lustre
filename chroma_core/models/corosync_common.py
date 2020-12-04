# -*- coding: utf-8 -*-
# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import logging

from django.db import models
from django.db.models import CASCADE

from chroma_core.models import AlertStateBase
from chroma_core.models import AlertEvent
from chroma_core.models import StateChangeJob
from chroma_core.models import NetworkInterface
from chroma_core.models.jobs import Job, StateLock
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_help.help import help_text


class StubCorosyncConfiguration(object):
    """
    This object allows us to create a stub for all the properties that will be referenced, maybe a better Python
    way and I can work on that.
    """

    host = None


class CorosyncUnknownPeersAlert(AlertStateBase):
    """Alert should be raised when a Host has an unknown Peer.

    When a corosync agent reports a peer that we do not know, we should raise an alert.
    """

    # This is worse than INFO because it *could* indicate that
    # networking is misconfigured..
    default_severity = logging.WARNING

    def alert_message(self):
        return "Host has unknown peer %s" % self.alert_item.host

    class Meta:
        app_label = "chroma_core"
        proxy = True

    @property
    def affected_objects(self):
        """
        :return: A list of objects that are affected by this alert
        """
        return [self.alert_item.host]


class CorosyncToManyPeersAlert(AlertStateBase):
    """Alert should be raised when a Host has an unknown Peer.

    When a corosync agent reports a peer that we do not know, we should raise an alert.
    """

    # This is worse than INFO because it *could* indicate that
    # networking is misconfigured..
    default_severity = logging.WARNING

    def alert_message(self):
        return "Host %s has to many failover pears" % self.alert_item.host

    class Meta:
        app_label = "chroma_core"
        proxy = True

    @property
    def affected_objects(self):
        """
        :return: A list of objects that are affected by this alert
        """
        return [self.alert_item.host]


class CorosyncNoPeersAlert(AlertStateBase):
    """Alert should be raised when a Host has an unknown Peer.

    When a corosync agent reports a peer that we do not know, we should raise an alert.
    """

    # This is worse than INFO because it *could* indicate that
    # networking is misconfigured..
    default_severity = logging.WARNING

    def alert_message(self):
        return "Host %s no failover peers" % self.alert_item.host

    class Meta:
        app_label = "chroma_core"
        proxy = True

    @property
    def affected_objects(self):
        """
        :return: A list of objects that are affected by this alert
        """
        return [self.alert_item.host]


class CorosyncStoppedAlert(AlertStateBase):
    # Corosync being down is never solely responsible for a filesystem
    # being unavailable: if a target is offline we will get a separate
    # ERROR alert for that.  Corosync being offline may indicate a configuration
    # fault, but equally could just indicate that the host hasn't booted up that far yet.
    default_severity = logging.INFO

    def alert_message(self):
        return "Corosync stopped on server %s" % self.alert_item.host

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def end_event(self):
        return AlertEvent(
            message_str="Corosync started on server '%s'" % self.alert_item.host,
            alert_item=self.alert_item.host,
            alert=self,
            severity=logging.WARNING,
        )

    @property
    def affected_objects(self):
        """
        :return: A list of objects that are affected by this alert
        """
        return [self.alert_item.host]


class AutoConfigureCorosyncJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(None, None, None)
    stateful_object = "corosync_configuration"
    corosync_configuration = StubCorosyncConfiguration()
    state_verb = "Configure Corosync"

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        abstract = True

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_corosync"]

    def description(self):
        return help_text["configure_corosync_on"] % self.corosync_configuration.host

    def get_deps(self):
        """
        Before Corosync operations are possible some dependencies are need, basically the host must have had its packages installed.
        Maybe we need a packages object, but this routine at least keeps the detail in one place.

        Or maybe we need an unacceptable_states lists.
        :return:
        """
        if self.corosync_configuration.host.state in ["unconfigured", "undeployed"]:
            return DependOn(self.corosync_configuration.host, "packages_installed")
        else:
            return DependAll()


class UnconfigureCorosyncJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(None, None, None)
    stateful_object = "corosync_configuration"
    corosync_configuration = StubCorosyncConfiguration()
    state_verb = "Unconfigure Corosync"

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        abstract = True

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unconfigure_corosync"]

    def description(self):
        return "Unconfigure Corosync on %s" % self.corosync_configuration.host

    @classmethod
    def can_run(cls, instance):
        """We don't want people to unconfigure corosync on a node that has a target so make the command
        available only when that is not the case.
        :param instance: CorosyncConfiguration instance being queried
        :return: True if no targets exist on the host in question.
        """
        from chroma_core.models.target import get_host_targets

        return len(get_host_targets(instance.host.id)) == 0


class StartCorosyncJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(None, None, None)
    stateful_object = "corosync_configuration"
    corosync_configuration = StubCorosyncConfiguration()
    state_verb = "Start Corosync"

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        abstract = True

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_corosync"]

    def description(self):
        return "Start Corosync on %s" % self.corosync_configuration.host


class StopCorosyncJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(None, None, None)
    stateful_object = "corosync_configuration"
    corosync_configuration = StubCorosyncConfiguration()
    state_verb = "Stop Corosync"

    display_group = Job.JOB_GROUPS.RARE
    display_order = 100

    class Meta:
        abstract = True

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["stop_corosync"]

    def description(self):
        return "Stop Corosync on %s" % self.corosync_configuration.host

    def get_deps(self):
        return DependOn(
            self.corosync_configuration.host.pacemaker_configuration, "stopped", unacceptable_states=["started"]
        )


class GetCorosyncStateStep(Step):
    idempotent = True

    # FIXME: using database=True to do the alerting update inside .set_state but
    # should do it in a completion
    database = True

    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        host = kwargs["host"]

        try:
            lnet_data = self.invoke_agent(host, "device_plugin", {"plugin": "linux_network"})["linux_network"]["lnet"]
            host.set_state(lnet_data["state"])
            host.save(update_fields=["state", "state_modified_at"])
        except TypeError:
            self.log("Data received from old client. Host %s state cannot be updated until agent is updated" % host)
        except AgentException as e:
            self.log("No data for plugin linux_network from host %s due to exception %s" % (host, e))


class GetCorosyncStateJob(Job):
    corosync_configuration = models.ForeignKey("CorosyncConfiguration", on_delete=CASCADE)

    requires_confirmation = False
    verb = "Get Corosync state"

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def create_locks(self):
        return [StateLock(job=self, locked_item=self.corosync_configuration, write=True)]

    @classmethod
    def get_args(cls, corosync_configuration):
        return {"host": corosync_configuration.host}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["corosync_state"]

    def description(self):
        return "Get Corosync state for %s" % self.corosync_configuration.host

    def get_steps(self):
        return [(GetCorosyncStateStep, {"host": self.corosync_configuration.host})]


class ConfigureCorosyncJob(Job):
    corosync_configuration = StubCorosyncConfiguration()
    network_interface_0 = models.ForeignKey(NetworkInterface, related_name="+", on_delete=CASCADE)
    network_interface_1 = models.ForeignKey(NetworkInterface, related_name="+", on_delete=CASCADE)
    mcast_port = models.IntegerField(null=True)

    class Meta:
        abstract = True

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_corosync_on"] % stateful_object.host.fqdn

    def description(self):
        return help_text["configure_corosync"]

    def get_deps(self):
        return DependOn(self.corosync_configuration, "stopped")
