
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from configure.lib.job import StateChangeJob, DependOn, DependAny, DependAll
from configure.models.jobs import StatefulObject, Job
from monitor.models import DeletableDowncastableMetaclass, MeasuredEntity


class ManagedFilesystem(StatefulObject, MeasuredEntity):
    __metaclass__ = DeletableDowncastableMetaclass
    name = models.CharField(max_length=8)
    mgs = models.ForeignKey('ManagedMgs')

    class Meta:
        unique_together = ('name', 'mgs')

    def get_targets(self):
        return [self.mgs.downcast()] + self.get_filesystem_targets()

    def get_filesystem_targets(self):
        from configure.models import ManagedOst, ManagedMdt
        osts = list(ManagedOst.objects.filter(filesystem = self).all())
        # NB using __str__ instead of name because name may not
        # be set in all cases
        osts.sort(lambda i, j: cmp(i.__str__()[-4:], j.__str__()[-4:]))

        return list(ManagedMdt.objects.filter(filesystem = self).all()) + osts

    def get_servers(self):
        from collections import defaultdict
        targets = self.get_targets()
        servers = defaultdict(list)
        for t in targets:
            for tm in t.managedtargetmount_set.all():
                servers[tm.host].append(tm)

        # NB converting to dict because django templates don't place nice with defaultdict
        # (http://stackoverflow.com/questions/4764110/django-template-cant-loop-defaultdict)
        return dict(servers)

    def status_string(self, target_statuses = None):
        if target_statuses == None:
            target_statuses = dict([(t, t.status_string()) for t in self.get_targets()])

        from configure.models.target import ManagedMgs
        filesystem_targets_statuses = [v for k, v in target_statuses.items() if not k.__class__ == ManagedMgs]
        all_statuses = target_statuses.values()

        good_status = set(["STARTED", "FAILOVER"])
        # If all my targets are down, I'm red, even if my MGS is up
        if not good_status & set(filesystem_targets_statuses):
            return "OFFLINE"

        # If all my targets are up including the MGS, then I'm green
        if set(all_statuses) <= set(["STARTED"]):
            return "OK"

        # Else I'm orange
        return "WARNING"

    def mgs_spec(self):
        """Return a string which is foo in <foo>:/lustre for client mounts"""
        mgs = self.mgs
        nid_specs = []
        for target_mount in mgs.managedtargetmount_set.all():
            host = target_mount.host
            nids = ",".join(host.lnetconfiguration.get_nids())
            if nids == "":
                raise ValueError("NIDs for MGS host %s not known" % host)

            nid_specs.append(nids)

        return ":".join(nid_specs)

    def mount_example(self):
        try:
            return "mount -t lustre %s:/%s /mnt/client" % (self.mgs_spec(), self.name)
        except ValueError, e:
            return "Not ready to mount: %s" % e

    def __str__(self):
        return self.name
    states = ['created', 'removed']
    initial_state = 'created'

    class Meta:
        app_label = 'configure'

    def get_conf_params(self):
        from itertools import chain
        from configure.models.conf_param import ConfParam
        params = chain(self.filesystemclientconfparam_set.all(), self.filesystemglobalconfparam_set.all())
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
