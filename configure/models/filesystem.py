
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from monitor import models as monitor_models
from configure.lib.job import StateChangeJob, DependOn, DependAny, DependAll
from configure.models.jobs import StatefulObject, Job

class ManagedFilesystem(monitor_models.Filesystem, StatefulObject):
    states = ['created', 'removed']
    initial_state = 'created'

    class Meta:
        app_label = 'configure'

    def get_conf_params(self):
        from itertools import chain
        from configure.models.conf_param import ConfParam
        params = chain(self.filesystemclientconfparam_set.all(),self.filesystemglobalconfparam_set.all())
        return ConfParam.get_latest_params(params)

    def get_deps(self, state = None):
        if not state:
            state = self.state
        
        mgs = self.mgs.downcast()
        allowed_mgs_states = set(mgs.states) - set(['removed'])
        if state != 'removed':
            return DependOn(mgs,
                    'unmounted',
                    acceptable_states = allowed_mgs_states,
                    fix_state = 'removed')
        else:
            return DependAll([])

    reverse_deps = {
            # FIXME: make jobs system smarter so that I can specify ManagedMgs here (currently
            # have to specify a direct descendent of StatefulObject, which in the case of all targets
            # is ManagedTarget)
            'ManagedTarget': lambda mmgs: ManagedFilesystem.objects.filter(mgs = mmgs)
            }

class RemoveFilesystemJob(Job, StateChangeJob):
    state_transition = (ManagedFilesystem, 'created', 'removed')
    stateful_object = 'filesystem'
    state_verb = "Remove"
    filesystem = models.ForeignKey('ManagedFilesystem')

    class Meta:
        app_label = 'configure'

    def description(self):
        return "Removing filesystem %s from configuration" % (self.filesystem.name)

    def get_steps(self):
        from configure.lib.job import DeleteFilesystemStep
        return [(DeleteFilesystemStep, {'filesystem_id': self.filesystem.id})]

MyModel = type('MyModel', (models.Model,), {
    'field': models.BooleanField(),
    '__module__': __name__,
})
