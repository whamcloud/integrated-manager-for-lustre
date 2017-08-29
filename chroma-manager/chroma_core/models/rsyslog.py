# -*- coding: utf-8 -*-
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models

from chroma_core.models import DeletableStatefulObject
from chroma_core.models import StateChangeJob
from chroma_core.models import Job
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_help.help import help_text


class RSyslogConfiguration(DeletableStatefulObject):
    states = ['unconfigured', 'configured']
    initial_state = 'unconfigured'

    host = models.OneToOneField('ManagedHost', related_name='_rsyslog_configuration')

    def __str__(self):
        return "%s RSyslog configuration" % self.host

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_label(self):
        return "rsyslog configuration"

    reverse_deps = {
        'ManagedHost': lambda mh: RSyslogConfiguration.objects.filter(host_id = mh.id),
    }


class ConfigureRsyslogStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs['rsyslog_configuration'].host, 'configure_rsyslog')


class ConfigureRsyslogJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(RSyslogConfiguration, 'unconfigured', 'configured')
    stateful_object = 'rsyslog_configuration'
    rsyslog_configuration = models.ForeignKey(RSyslogConfiguration)
    state_verb = 'Start RSyslog'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["configure_rsyslog"]

    def description(self):
        return "Configure RSyslog on %s" % self.rsyslog_configuration.host

    def get_steps(self):
        return [(ConfigureRsyslogStep, {'rsyslog_configuration': self.rsyslog_configuration})]

    def get_deps(self):
        '''
        Before rsyslong operations are possible some dependencies are need, basically the host must have had its packages installed.
        Maybe we need a packages object, but this routine at least keeps the detail in one place.

        Or maybe we need an unacceptable_states lists.
        :return:
        '''
        if self.rsyslog_configuration.host.state in ['unconfigured', 'undeployed']:
            return DependOn(self.rsyslog_configuration.host, 'packages_installed')
        else:
            return DependAll()


class UnconfigureRsyslogStep(Step):
    idempotent = True

    def run(self, kwargs):
        self.invoke_agent_expect_result(kwargs['rsyslog_configuration'].host, "unconfigure_rsyslog")


class UnconfigureRsyslogJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(RSyslogConfiguration, 'configured', 'unconfigured')
    stateful_object = 'rsyslog_configuration'
    rsyslog_configuration = models.ForeignKey(RSyslogConfiguration)
    state_verb = 'Unconfigure RSyslog'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unconfigure_rsyslog"]

    def description(self):
        return "Unconfigure RSyslog on %s" % self.rsyslog_configuration.host

    def get_steps(self):
        return [(UnconfigureRsyslogStep, {'rsyslog_configuration': self.rsyslog_configuration})]
