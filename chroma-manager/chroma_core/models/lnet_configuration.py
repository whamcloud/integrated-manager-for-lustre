# -*- coding: utf-8 -*-
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

import json
import re
from collections import namedtuple

from django.db import models

from django.core.exceptions import ObjectDoesNotExist


from chroma_core.models.jobs import StateChangeJob
from chroma_core.models.jobs import Job, StateLock
from chroma_core.models.host import NetworkInterface, UpdateDevicesStep
from chroma_core.models.host import ManagedHost
from chroma_core.lib.job import DependOn, Step
from chroma_help.help import help_text


class LNetConfiguration(models.Model):
    # Chris: This will move to a stateful object at some point
    #StatefulObject):
    #states = ['nids_unknown', 'nids_known']
    #initial_state = 'nids_unknown'

    host = models.OneToOneField('ManagedHost')

    # Valid states are 'lnet_up', 'lnet_down', 'lnet_unloaded'. As we fully implement dynamic lnet these object
    # may go back to being a StatefulObject but we need to do this one step at a time. So for now we just do it
    # like this.
    state = models.CharField(max_length = 16, help_text = "The current state of the lnet configuration")

    def get_nids(self):
        return [n.nid_string for n in self.nid_set.all()]

    def __str__(self):
        return "%s LNet configuration" % (self.host)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class ConfigureLNetStep(Step):
    idempotent = True

    # FIXME: using database=True to do the alerting update inside .set_state but
    # should do it in a completion
    database = True

    def run(self, kwargs):
        host = kwargs['host']
        nid_updates = kwargs['config_changes']['nid_updates']
        nid_deletes = kwargs['config_changes']['nid_deletes']

        modprobe_entries = []
        nid_tuples = []

        network_interfaces = NetworkInterface.objects.filter(host=host)
        lnet_configuration = LNetConfiguration.objects.get(host=host)

        for network_interface in network_interfaces:
            # See if we have deleted the nid for this network interface or
            # see if we have a new configuration for this if we do then it
            # will replace the current configuration.
            #
            # The int will have become a string - we should use a PickledObjectField really.
            if str(network_interface.id) in nid_deletes:
                nid = None
            elif str(network_interface.id) in nid_updates:
                nid = Nid(network_interface = network_interface,
                          lnet_configuration = lnet_configuration,
                          lnd_network = nid_updates[str(network_interface.id)]['lnd_network'])
            else:
                try:
                    nid = Nid.objects.get(network_interface = network_interface)
                except ObjectDoesNotExist:
                    nid = None
                    pass

            if nid is not None:
                modprobe_entries.append(nid.modprobe_entry)
                nid_tuples.append(nid.to_tuple)

        self.invoke_agent(host,
                          "configure_lnet",
                          {'lnet_configuration': {'state': lnet_configuration.state,
                                                  'modprobe_entries': modprobe_entries,
                                                  'network_interfaces': nid_tuples}})


class UnconfigureLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure_lnet")


class ConfigureLNetJob(Job):
    host = models.ForeignKey(ManagedHost)
    config_changes = models.CharField(max_length = 4096, help_text = "A json string describing the configuration changes")
    requires_confirmation = False
    state_verb = "Configure LNet"

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def create_locks(self):
        return [StateLock(
            job = self,
            locked_item = self.host,
            write = True
        )]

    @classmethod
    def get_args(cls, lnet_configuration):
        return {'lnet_configuration': lnet_configuration}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['configure_lnet']

    def description(self):
        return "Configure LNet for %s" % self.host

    def get_steps(self):
        # The get_deps means the lnet is always placed into the unloaded state in preparation for the change in
        # configure the next two steps cause lnet to return to the state it was in
        steps = [(ConfigureLNetStep, {'host': self.host, 'config_changes': json.loads(self.config_changes)})]

        if (self.state != 'lnet_unloaded'):
            steps.append((LoadLNetStep, {'host': self.host}))

        if (self.state == 'lnet_up'):
            steps.append((StartLNetStep, {'host': self.host}))

        steps.append((UpdateDevicesStep, {'host': self.host}))

        return steps

    def get_deps(self):
        return DependOn(self.host, 'lnet_unloaded')


class StartLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "start_lnet")


class StopLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "stop_lnet")


class LoadLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "load_lnet")


class UnloadLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "unload_lnet")


class LoadLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Load LNet'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_lnet"]

    def description(self):
        return "Load LNet module on %s" % self.host

    def get_steps(self):
        return [(LoadLNetStep, {'host': self.host}),
                (UpdateDevicesStep, {'host': self.host})]


class StartLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Start LNet'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 40

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_lnet"]

    def description(self):
        return "Start LNet on %s" % self.host

    def get_steps(self):
        return [(StartLNetStep, {'host': self.host}),
                (UpdateDevicesStep, {'host': self.host})]


class StopLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Stop LNet'

    display_group = Job.JOB_GROUPS.RARE
    display_order = 100

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["stop_lnet"]

    def description(self):
        return "Stop LNet on %s" % self.host

    def get_steps(self):
        return [(StopLNetStep, {'host': self.host}),
                (UpdateDevicesStep, {'host': self.host})]


class Nid(models.Model):
    """Simplified NID representation for those we detect already-configured"""
    lnet_configuration = models.ForeignKey(LNetConfiguration)
    network_interface = models.OneToOneField(NetworkInterface, primary_key = True)

    lnd_network = models.IntegerField(null=True)

    @property
    def nid_string(self):
        return ("%s@%s%s" % (self.network_interface.inet4_address,
                             self.network_interface.type,
                             self.lnd_network))

    @property
    def modprobe_entry(self):
        return("%s%s(%s)" % (self.network_interface.type,
                             self.lnd_network,
                             self.network_interface.name))

    @property
    def to_tuple(self):
        return tuple([self.network_interface.inet4_address,
                      self.network_interface.type,
                      self.lnd_network])

    @classmethod
    def nid_tuple_to_string(cls, nid):
        return ("%s@%s%s" % (nid.nid_address,
                             nid.lnd_type,
                             nid.lnd_network))

    Nid = namedtuple("Nid", ["nid_address", "lnd_type", "lnd_network"])

    @classmethod
    def split_nid_string(cls, nid_string):
        '''
        :param nid_string: Can be multiple format tcp0, tcp, tcp1234, o2ib0, o2ib (not number in the word)
        :return: Nid name tuple containing the address, the lnd_type or the lnd_network
        '''
        assert '@' in nid_string, "Malformed NID?!: %s"

        # Split the nid so we can search correctly on its parts.
        nid_address = nid_string.split("@")[0]
        type_network_no = nid_string.split("@")[1]
        m = re.match('(\w+?)(\d+)?$', type_network_no)   # Non word, then optional greedy number at end of line.
        lnd_type = m.group(1)
        lnd_network = m.group(2)
        if not lnd_network:
            lnd_network = 0

        return Nid.Nid(nid_address, lnd_type, lnd_network)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['network_interface']
