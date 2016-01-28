# -*- coding: utf-8 -*-
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.

import threading
from collections import defaultdict

from django.utils.timezone import now
from django.db import models

from chroma_core.services import log_register
from chroma_core.models import CorosyncConfiguration
from chroma_core.models import corosync_common
from chroma_core.lib.job import Step
from chroma_core.services.job_scheduler import job_scheduler_notify

peer_mcast_ports = {}

logging = log_register('corosync2')


def _corosync_peers(new_fqdn, mcast_port):
    """Because the mcast_ports are deemed to be unique, in fact we work hard to make them
    unique we can say that all configured (!unconfigured) corosync configurations with the same
    mcast port and same mcast address are peers

    :param new_fqdn: str The fqdn of the new node we are looking for matching mcast ports.
    :param mcast_port: int The mcast_port to look up and by inference the mcast_port of the new_fqdn.
    :return: List of fqdns of the peers.
    """

    # Need to keep in sync with the DB so update from the DB before anything else.
    current_db_entries = {}
    for corosync_configuration in Corosync2Configuration.objects.filter(~models.Q(mcast_port=None)):
        current_db_entries[corosync_configuration.host.fqdn] = corosync_configuration.mcast_port
        peer_mcast_ports[corosync_configuration.host.fqdn] = corosync_configuration.mcast_port

    # Now we need to remove any corosync configurations that have been deleted.
    for corosync_configuration in Corosync2Configuration._base_manager.filter(not_deleted=None):
        # Only remove the entries that are not currently in the db - a host may be deleted and re-added
        if corosync_configuration.host.fqdn not in current_db_entries:
            peer_mcast_ports.pop(corosync_configuration.host.fqdn, None)

    # Do this at the end because this could be different from the DB if this is an update.
    peer_mcast_ports[new_fqdn] = mcast_port

    # Return list of peers, but peers do not include ourselves.
    peers = [match_fqdn for match_fqdn, match_mcast_port in peer_mcast_ports.items() if match_mcast_port == mcast_port]
    peers.remove(new_fqdn)

    return peers


class Corosync2Configuration(CorosyncConfiguration):
    # We want separate versions from the CorosyncConfiguration
    route_map = None
    transition_map = None
    job_class_map = None

    def __str__(self):
        return "%s Corosync2 configuration" % self.host

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_label(self):
        return "corosync2 configuration"

    reverse_deps = {
        'ManagedHost': lambda mh: Corosync2Configuration.objects.filter(host_id = mh.id),
    }

    # This is temporary, although will work perfectly functionally. Once landed we will move to
    #  use the sparse table functionality.
    def save(self, force_insert=False, force_update=False, using=None):
        self.record_type = "Corosync2Configuration"
        return super(Corosync2Configuration, self).save(force_insert, force_update, using)

    @property
    def configure_job_name(self):
        return "ConfigureCorosync2Job"

# Semaphore for operations so that when we configure corosync for each HA cluster we configure
# one node at a time hence removing any race conditions.
peer_mcast_ports_configuration_lock = defaultdict(lambda: threading.RLock())


class AutoConfigureCorosyncStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        corosync_configuration = kwargs['corosync_configuration']

        # detect local interfaces for use in corosync 'rings', network level configuration only
        config = self.invoke_agent_expect_result(corosync_configuration.host, "get_corosync_autoconfig")

        ring0_name, ring0_config = next((interface, config) for interface, config in
                                        config['interfaces'].items() if config['dedicated'] == False)
        ring1_name, ring1_config = next((interface, config) for interface, config in
                                        config['interfaces'].items() if config['dedicated'] == True)

        # apply the configurations of corosync 'rings', network level configuration only
        self.invoke_agent_expect_result(corosync_configuration.host,
                                        "configure_network",
                                        {'ring0_name': ring0_name,
                                         'ring1_name': ring1_name,
                                         'ring1_ipaddr': ring1_config['ipaddr'],
                                         'ring1_prefix': ring1_config['prefix']})

        logging.debug("Node %s returned corosync configuration %s" % (corosync_configuration.host.fqdn,
                                                                     config))

        # Serialize across nodes with the same mcast_port so that we ensure commands
        # are executed in the same order.
        with peer_mcast_ports_configuration_lock[config['mcast_port']]:
            from chroma_core.models import ManagedHost

            corosync_peers = _corosync_peers(corosync_configuration.host.fqdn, config['mcast_port'])

            logging.debug("Node %s has corosync peers %s" % (corosync_configuration.host.fqdn,
                                                            ",".join(corosync_peers)))

            # If we are adding then we action on a host that is already part of the cluster
            # otherwise we have to action on the host we are adding because it is the first node in the cluster
            # TODO: Harden this up a little so it tries to pick a peer that is actively communicating, might be useful
            # when adding a new host in place of an old host.
            if corosync_peers:
                actioning_host_fqdn = corosync_peers[0]
            else:
                actioning_host_fqdn = corosync_configuration.host.fqdn

            actioning_host = ManagedHost.objects.get(fqdn = actioning_host_fqdn)

            # Stage 1 configures pcsd on the host being added, sets the password, enables and starts it etc.
            self.invoke_agent_expect_result(corosync_configuration.host,
                                            "configure_corosync2_stage_1")

            # Stage 2 configures the cluster either by creating it or adding a node to it.
            self.invoke_agent_expect_result(actioning_host,
                                            "configure_corosync2_stage_2",
                                            {'ring0_name': ring0_name,
                                             'ring1_name': ring1_name,
                                             'new_node_fqdn': corosync_configuration.host.fqdn,
                                             'mcast_port': config['mcast_port'],
                                             'create_cluster': actioning_host_fqdn == corosync_configuration.host.fqdn})

            logging.debug("Node %s corosync configuration complete" % corosync_configuration.host.fqdn)

        job_scheduler_notify.notify(corosync_configuration,
                                    now(),
                                    {'mcast_port': config['mcast_port'],
                                     'network_interfaces': [ring0_name, ring1_name]})


class AutoConfigureCorosync2Job(corosync_common.AutoConfigureCorosyncJob):
    state_transition = corosync_common.AutoConfigureCorosyncJob.StateTransition(Corosync2Configuration,
                                                                                'unconfigured',
                                                                                'stopped')
    corosync_configuration = models.ForeignKey(Corosync2Configuration)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_steps(self):
        return [(AutoConfigureCorosyncStep, {'corosync_configuration': self.corosync_configuration})]


class UnconfigureCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs['host'],
                                        "unconfigure_corosync2",
                                        {'host_fqdn': kwargs['host'].fqdn,
                                         'mcast_port': kwargs['mcast_port']})


class UnconfigureCorosync2Job(corosync_common.UnconfigureCorosyncJob):
    state_transition = corosync_common.UnconfigureCorosyncJob.StateTransition(Corosync2Configuration, 'stopped', 'unconfigured')
    corosync_configuration = models.ForeignKey(Corosync2Configuration)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_steps(self):
        return [(UnconfigureCorosyncStep, {'host': self.corosync_configuration.host,
                                           'mcast_port': self.corosync_configuration.mcast_port})]


class StartCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs['host'], "start_corosync2")


class StartCorosync2Job(corosync_common.StartCorosyncJob):
    state_transition = corosync_common.StartCorosyncJob.StateTransition(Corosync2Configuration, 'stopped', 'started')
    corosync_configuration = models.ForeignKey(Corosync2Configuration)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_steps(self):
        return [(StartCorosyncStep, {'host': self.corosync_configuration.host})]


class StopCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs['host'], "stop_corosync2")


class StopCorosync2Job(corosync_common.StopCorosyncJob):
    state_transition = corosync_common.StopCorosyncJob.StateTransition(Corosync2Configuration, 'started', 'stopped')
    corosync_configuration = models.ForeignKey(Corosync2Configuration)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_steps(self):
        return [(StopCorosyncStep, {'host': self.corosync_configuration.host})]


class ConfigureCorosyncStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        corosync_configuration = kwargs['corosync_configuration']

        self.invoke_agent_expect_result(corosync_configuration.host,
                                        "configure_corosync2",
                                        {'peer_fqdns': kwargs['peer_fqdns'],
                                         'ring0_name': kwargs['ring0_name'],
                                         'ring1_name': kwargs['ring1_name'],
                                         'mcast_port': kwargs['mcast_port']})

        job_scheduler_notify.notify(corosync_configuration,
                                    now(),
                                    {'mcast_port': kwargs['mcast_port'],
                                     'network_interfaces': [kwargs['ring0_name'], kwargs['ring1_name']]})


class ConfigureCorosync2Job(corosync_common.ConfigureCorosyncJob):
    corosync_configuration = models.ForeignKey(Corosync2Configuration)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_steps(self):
        steps = [(ConfigureCorosyncStep, {'corosync_configuration': self.corosync_configuration,
                                          'peer_fqdns': _corosync_peers(self.corosync_configuration.host.fqdn,
                                                                        self.corosync_configuration.mcast_port),
                                          'ring0_name': self.network_interface_0.name,
                                          'ring1_name': self.network_interface_1.name,
                                          'mcast_port': self.mcast_port})]

        return steps
