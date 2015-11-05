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

import socket

from django.db import models

from chroma_core.models import DeletableStatefulObject
from chroma_core.models import StateChangeJob
from chroma_core.models import Job
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_help.help import help_text

import settings


class NTPConfiguration(DeletableStatefulObject):
    states = ['unconfigured', 'configured']
    initial_state = 'unconfigured'

    host = models.OneToOneField('ManagedHost', related_name='_ntp_configuration')

    def __str__(self):
        return "%s NTP configuration" % self.host

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_label(self):
        return "ntp configuration"

    reverse_deps = {
        'ManagedHost': lambda mh: NTPConfiguration.objects.filter(host_id = mh.id),
    }


class ConfigureNtpStep(Step):
    idempotent = True

    def run(self, kwargs):
        if settings.NTP_SERVER_HOSTNAME:
            ntp_server = settings.NTP_SERVER_HOSTNAME
        else:
            ntp_server = socket.getfqdn()

        self.invoke_agent_expect_result(kwargs['ntp_configuration'].host, "configure_ntp", {'ntp_server': ntp_server})


class ConfigureNtpJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(NTPConfiguration, 'unconfigured', 'configured')
    stateful_object = 'ntp_configuration'
    ntp_configuration = models.ForeignKey(NTPConfiguration)
    state_verb = 'Start Ntp'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_ntp"]

    def description(self):
        return "Configure NTP on %s" % self.ntp_configuration.host

    def get_steps(self):
        return [(ConfigureNtpStep, {'ntp_configuration': self.ntp_configuration})]

    def get_deps(self):
        '''
        Before ntp operations are possible some dependencies are need, basically the host must have had its packages installed.
        Maybe we need a packages object, but this routine at least keeps the detail in one place.

        Or maybe we need an unacceptable_states lists.
        :return:
        '''
        if self.ntp_configuration.host.state in ['unconfigured', 'undeployed']:
            return DependOn(self.ntp_configuration.host, 'packages_installed')
        else:
            return DependAll()


class UnconfigureNtpStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs['ntp_configuration'].host, "unconfigure_ntp")


class UnconfigureNtpJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(NTPConfiguration, 'configured', 'unconfigured')
    stateful_object = 'ntp_configuration'
    ntp_configuration = models.ForeignKey(NTPConfiguration)
    state_verb = 'Unconfigure NTP'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unconfigure_ntp"]

    def description(self):
        return "Unconfigure Ntp on %s" % self.ntp_configuration.host

    def get_steps(self):
        return [(UnconfigureNtpStep, {'ntp_configuration': self.ntp_configuration})]
