#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import functools

# HYD-646: Use django 1.4 db exceptions
import MySQLdb as Database
from django.db import transaction

from chroma_core.models.target import ManagedMdt, ManagedTarget, TargetRecoveryInfo, TargetRecoveryAlert
from chroma_core.models.host import ManagedHost, HostContactAlert, LNetNidsChangedAlert, NoLNetInfo
from chroma_core.lib.state_manager import StateManagerClient
from chroma_core.models import ManagedTargetMount

import settings

audit_log = settings.setup_log('audit')


def normalize_nid(string):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow
       direct comparisons between NIDs"""
    if string[-4:] == "@tcp":
        string += "0"

    # remove _ from nids (i.e. @tcp_0 -> @tcp0
    i = string.find("_")
    if i > -1:
        string = string[:i] + string[i + 1:]

    return string


def normalize_nids(nid_list):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow
       direct comparisons between NIDs"""
    return [normalize_nid(n) for n in nid_list]


class UpdateScan(object):
    def __init__(self):
        self.audited_mountables = {}
        self.host = None
        self.host_data = None

    def is_valid(self):
        try:
            assert(isinstance(self.host_data, dict))
            assert('lnet_up' in self.host_data)
            assert('lnet_loaded' in self.host_data)
            assert('mounts' in self.host_data)
            assert('metrics' in self.host_data)
            assert('resource_locations' in self.host_data)
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    @transaction.commit_on_success
    def audit_host(self):
        if isinstance(self.host_data, Exception):
            audit_log.error("exception contacting %s: %s" % (self.host, self.host_data))
            contact = False
        elif not self.is_valid():
            audit_log.error("invalid output from %s: %s" % (self.host, self.host_data))
            contact = False
        else:
            contact = True

            self.learn_capabilities()

            self.update_lnet()
            self.update_resource_locations()
            self.update_target_mounts()

        HostContactAlert.notify(self.host, not contact)

        if contact:
            from datetime import datetime
            ManagedHost.objects.filter(pk = self.host.pk).update(last_contact = datetime.utcnow())

        return contact

    def run(self, host_id, started_at, host_data):
        host = ManagedHost.objects.get(pk=host_id)
        self.started_at = started_at
        self.host = host
        self.host_data = host_data
        audit_log.debug("UpdateScan.run: %s" % self.host)

        contact = self.audit_host()
        self.store_metrics()

        return contact

    def learn_capabilities(self):
        """Update the host record from the capabilities reported by the agent"""
        # FIXME: What to do if we split out rsyslog into an optional
        # package?  Rename it to configure_rsyslog?

        if len([c for c in self.host_data['capabilities'] if "manage_" in c]) > 0:
            return
        else:
            if not self.host.immutable_state:
                audit_log.debug("Setting immutable_state flag on %s" % self.host)
                self.host.immutable_state = True
                self.host.save()

    def update_lnet(self):
        # Update LNet status
        lnet_state = {(False, False): 'lnet_unloaded',
                (True, False): 'lnet_down',
                (True, True): 'lnet_up'}[(self.host_data['lnet_loaded'],
                                          self.host_data['lnet_up'])]

        StateManagerClient.notify_state(self.host.downcast(),
                                  self.started_at,
                                  lnet_state,
                                  ['lnet_unloaded', 'lnet_down', 'lnet_up'])

        try:
            known_nids = self.host.lnetconfiguration.get_nids()
        except NoLNetInfo:
            pass
        else:
            if self.host_data['lnet_nids']:
                current = (set(known_nids) == set([normalize_nid(n) for n in self.host_data['lnet_nids']]))
                LNetNidsChangedAlert.notify(self.host, not current)

    def update_target_mounts(self):
        # Loop over all mountables we expected on this host, whether they
        # were actually seen in the results or not.
        mounted_uuids = dict([(m['fs_uuid'], m) for m in self.host_data['mounts']])
        for target_mount in ManagedTargetMount.objects.filter(host = self.host):

            # Mounted-ness
            # ============
            mounted_locally = target_mount.target.uuid in mounted_uuids

            # Recovery status
            # ===============
            if mounted_locally:
                mount_info = mounted_uuids[target_mount.target.uuid]
                recovery_status = mount_info["recovery_status"]
            else:
                recovery_status = {}

            # Update to active_mount and alerts for monitor-only
            # targets done here instead of resource_locations
            if target_mount.target.immutable_state:
                target = target_mount.target
                if mounted_locally:
                    target.set_active_mount(target_mount)
                    StateManagerClient.notify_state(target, self.started_at, 'mounted', ['mounted', 'unmounted'])
                elif not mounted_locally and target.active_mount == target_mount:
                    target.set_active_mount(None)
                    StateManagerClient.notify_state(target, self.started_at, 'unmounted', ['mounted', 'unmounted'])

            if target_mount.target.active_mount == None:
                TargetRecoveryInfo.update(target_mount.target, {})
                TargetRecoveryAlert.notify(target_mount.target, False)
            elif mounted_locally:
                recovering = TargetRecoveryInfo.update(target_mount.target, recovery_status)
                TargetRecoveryAlert.notify(target_mount.target, recovering)

    def update_resource_locations(self):
        if self.host_data['resource_locations'] == None:
            # None here means that it was not possible to obtain a
            # list from corosync: corosync may well be absent if
            # we're monitoring a non-chroma-managed monitor-only
            # system.  But if there are managed mounts
            # then this is a problem.
            if ManagedTarget.objects.filter(immutable_state = False, managedtargetmount__host = self.host).count():
                audit_log.error("Got no resource_locations from host %s, but there are chroma-configured mounts on that server!" % self.host)
            return

        for resource_name, node_name in self.host_data['resource_locations'].items():
            try:
                target = ManagedTarget.objects.get(ha_label = resource_name).downcast()
            except ManagedTarget.DoesNotExist:
                #audit_log.warning("Resource %s on host %s is not a known target" % (resource_name, self.host))
                continue

            # If we're operating on a Managed* rather than a purely monitored target
            if not target.immutable_state:
                if node_name == None:
                    active_mount = None
                else:
                    try:
                        host = ManagedHost.objects.get(nodename = node_name)
                        try:
                            active_mount = ManagedTargetMount.objects.get(target = target, host = host)
                        except ManagedTargetMount.DoesNotExist:
                            audit_log.warning("Resource for target '%s' is running on host '%s', but there is no such TargetMount" % (target, host))
                            active_mount = None
                    except ManagedHost.DoesNotExist:
                        audit_log.warning("Resource location node '%s' does not match any Host" % (node_name))
                        active_mount = None

                target.set_active_mount(active_mount)

                state = ['unmounted', 'mounted'][active_mount != None]
                from chroma_core.lib.state_manager import StateManagerClient
                StateManagerClient.notify_state(target, self.started_at, state, ['mounted', 'unmounted'])

    def store_lustre_target_metrics(self, target_name, metrics):
        # TODO: Re-enable MGS metrics storage if it turns out it's useful.
        if target_name == "MGS":
            return 0

        try:
            target = ManagedTarget.objects.get(name=target_name,
                                        managedtargetmount__host=self.host).downcast()
        except ManagedTarget.DoesNotExist:
            # Unknown target -- ignore metrics
            audit_log.warning("Discarding metrics for unknown target: %s" % target_name)
            return 0

        # Synthesize the 'client_count' metric (assumes one MDT per filesystem)
        if isinstance(target, ManagedMdt):
            metrics['client_count'] = metrics['num_exports'] - 1

        return target.metrics.update(metrics, self.update_time)

    def store_node_metrics(self, metrics):
        return self.host.downcast().metrics.update(metrics, self.update_time)

    def catch_metrics_deadlocks(fn):
        # This decorator is specific to catching deadlocks which may occur
        # during an r3d update.  Ideally, these shouldn't happen at all, but
        # if they do they shouldn't be fatal.  In any case, we need to log
        # warnings so we can keep track of this and figure out if it's really
        # a problem, and if it is, whether to fix it in code or in db tuning.
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Database.OperationalError, e:
                if e[0] == 1213:
                    audit_log.warn("Caught deadlock on metrics update; discarding metrics and continuing")
                    return 0

                raise e
        return wrapper

    @catch_metrics_deadlocks
    @transaction.commit_on_success
    def store_metrics(self):
        """
        Pass the received metrics into the metrics library for storage.
        """
        raw_metrics = self.host_data['metrics']['raw']
        count = 0

        if not hasattr(self, 'update_time'):
            self.update_time = None

        try:
            node_metrics = raw_metrics['node']
            try:
                node_metrics['lnet'] = raw_metrics['lustre']['lnet']
            except KeyError:
                pass

            count += self.store_node_metrics(node_metrics)
        except KeyError:
            pass

        try:
            for target in raw_metrics['lustre']['target']:
                target_metrics = raw_metrics['lustre']['target'][target]
                count += self.store_lustre_target_metrics(target, target_metrics)
        except KeyError:
            pass

        return count
