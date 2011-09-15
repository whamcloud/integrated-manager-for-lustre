
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from monitor import models as monitor_models
from configure.models.jobs import StatefulObject, Job
from configure.lib.job import StateChangeJob, DependOn, DependAny, DependAll


class ManagedHost(monitor_models.Host, StatefulObject):
    # TODO: separate the LNET state [unloaded, down, up] from the host state [created, removed]
    states = ['lnet_unloaded', 'lnet_down', 'lnet_up', 'removed']
    initial_state = 'lnet_unloaded'

    class Meta:
        app_label = 'configure'

    def save(self, *args, **kwargs):
        new = (self.pk == None)
        super(ManagedHost, self).save(*args, **kwargs)
        if new:
            assert(self.pk != None)
            from configure.lib.state_manager import StateManager
            StateManager().add_job(AddHostJob(host = self))

class LoadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Load LNet'

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Loading LNet module on %s" % self.host

    def get_steps(self):
        from configure.lib.job import LoadLNetStep
        return [(LoadLNetStep, {'host_id': self.host.id})]

class UnloadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Unload LNet'

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Unloading LNet module on %s" % self.host

    def get_steps(self):
        from configure.lib.job import UnloadLNetStep
        return [(UnloadLNetStep, {'host_id': self.host.id})]
    
class StartLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Start LNet'

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Start LNet on %s" % self.host

    def get_steps(self):
        from configure.lib.job import StartLNetStep
        return [(StartLNetStep, {'host_id': self.host.id})]

class StopLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Stop LNet'

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Stop LNet on %s" % self.host

    def get_steps(self):
        from configure.lib.job import StopLNetStep
        return [(StopLNetStep, {'host_id': self.host.id})]

class RemoveHostJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'removed')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Remove'

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        from configure.lib.job import DeleteHostStep
        return [(DeleteHostStep, {'host_id': self.host.id})]

class AddHostJob(Job):
    host = models.ForeignKey(ManagedHost)
    class Meta:
        app_label = 'configure'

    def description(self):
        return "Adding new host %s" % self.host

    def get_steps(self):
        from configure.lib.job import AddHostStep
        return [(AddHostStep, {'host_id': self.host.id})]

