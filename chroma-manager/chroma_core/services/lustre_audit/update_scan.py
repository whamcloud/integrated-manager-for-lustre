#!/usr/bin/env python
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


from chroma_core.services import log_register
import dateutil.parser
from django.db import transaction

from chroma_core.models.target import ManagedTarget, TargetRecoveryInfo, TargetRecoveryAlert
from chroma_core.models.host import ManagedHost
from chroma_core.models.client_mount import LustreClientMount
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.models import ManagedTargetMount
import chroma_core.models.package
from chroma_core.services.stats import StatsQueue


log = log_register(__name__)


class UpdateScan(object):
    def __init__(self):
        self.audited_mountables = {}
        self.host = None
        self.host_data = None

    def is_valid(self):
        try:
            assert(isinstance(self.host_data, dict))
            assert('mounts' in self.host_data)
            assert('metrics' in self.host_data)
            assert('resource_locations' in self.host_data)
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    @transaction.commit_on_success
    def audit_host(self):
        self.update_packages(self.host_data['packages'])
        self.update_resource_locations()
        self.update_target_mounts()
        self.update_client_mounts()

    def run(self, host_id, host_data):
        host = ManagedHost.objects.get(pk=host_id)
        self.started_at = dateutil.parser.parse(host_data['started_at'])
        self.host = host
        self.host_data = host_data
        log.debug("UpdateScan.run: %s" % self.host)

        self.audit_host()
        self.store_metrics()

    def update_packages(self, packages):
        if not packages:
            # Packages is allowed to be None
            # (means is not the initial message, or there was a problem talking to RPM or yum)
            return

        # An update is required if:
        #  * A package is installed on the storage server for which there is a more recent version
        #    available on the manager
        #  or
        #  * A package is available on the manager, and specified in the server's profile's list of
        #    packages, but is not installed on the storage server.

        # Update the package models
        needs_update = chroma_core.models.package.update(self.host, packages)

        # Check for any non-installed packages that should be installed
        for package in self.host.server_profile.serverprofilepackage_set.all():
            try:
                package_data = packages[package.bundle.bundle_name][package.package_name]
            except KeyError:
                log.warning("Expected package %s/%s not found in report from %s" % (
                    package.bundle.bundle_name, package.package_name, self.host))
                continue
            else:
                if not package_data['installed']:
                    log.info("Update available (not installed): %s/%s on %s" % (
                        package.bundle.bundle_name, package.package_name, self.host))
                    needs_update = True
                    break

        log.info("update_packages(%s): updates=%s" % (self.host, needs_update))
        JobSchedulerClient.notify(self.host, self.started_at, {'needs_update': needs_update})

    def update_client_mounts(self):
        # Client mount audit comes in via metrics due to the way the
        # ClientAudit is implemented.
        try:
            client_mounts = self.host_data['metrics']['raw']['lustre_client_mounts']
        except KeyError:
            client_mounts = []

        # If lustre_client_mounts is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no mounts
        if client_mounts == None:
            return

        expected_fs_mounts = LustreClientMount.objects.select_related('filesystem').filter(host = self.host)
        actual_fs_mounts = [m['mountspec'].split(':/')[1] for m in client_mounts]

        # Don't bother with the rest if there's nothing to do.
        if len(expected_fs_mounts) == 0 and len(actual_fs_mounts) == 0:
            return

        for expected_mount in expected_fs_mounts:
            if expected_mount.active and expected_mount.filesystem.name not in actual_fs_mounts:
                update = dict(state = 'unmounted', mountpoint = None)
                JobSchedulerClient.notify(expected_mount,
                                          self.started_at,
                                          update)
                log.info("updated mount %s on %s -> inactive" % (expected_mount.mountpoint, self.host))

        for actual_mount in client_mounts:
            fsname = actual_mount['mountspec'].split(':/')[1]
            try:
                mount = [m for m in expected_fs_mounts if m.filesystem.name == fsname][0]
                log.debug("mount: %s" % mount)
                if not mount.active:
                    update = dict(state = 'mounted',
                                  mountpoint = actual_mount['mountpoint'])
                    JobSchedulerClient.notify(mount,
                                              self.started_at,
                                              update)
                    log.info("updated mount %s on %s -> active" % (actual_mount['mountpoint'], self.host))
            except IndexError:
                log.info("creating new mount %s on %s" % (actual_mount['mountpoint'], self.host))
                filesystem = ManagedFilesystem.objects.get(name = fsname)
                JobSchedulerClient.create_client_mount(self.host,
                                                       filesystem,
                                                       actual_mount['mountpoint'])

    def update_target_mounts(self):
        # If mounts is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no mounts
        if self.host_data['mounts'] == None:
            return

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
                    JobSchedulerClient.notify(target, self.started_at, {
                        'state': 'mounted',
                        'active_mount_id': target_mount.id
                    }, ['mounted', 'unmounted'])
                elif not mounted_locally and target.active_mount == target_mount:
                    log.debug("clearing active_mount, %s %s", self.started_at, self.host)

                    JobSchedulerClient.notify(target, self.started_at, {
                        'state': 'unmounted',
                        'active_mount_id': None
                    }, ['mounted', 'unmounted'])

            if target_mount.target.active_mount == None:
                TargetRecoveryInfo.update(target_mount.target, {})
                TargetRecoveryAlert.notify(target_mount.target, False)
            elif mounted_locally:
                recovering = TargetRecoveryInfo.update(target_mount.target, recovery_status)
                TargetRecoveryAlert.notify(target_mount.target, recovering)

    def update_resource_locations(self):
        # If resource_locations is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no resource_locations
        if self.host_data['resource_locations'] == None:
            return

        if 'crm_mon_error' in self.host_data['resource_locations']:
            # Means that it was not possible to obtain a
            # list from corosync: corosync may well be absent if
            # we're monitoring a non-chroma-managed monitor-only
            # system.  But if there are managed mounts
            # then this is a problem.
            crm_mon_error = self.host_data['resource_locations']['crm_mon_error']
            if ManagedTarget.objects.filter(immutable_state = False, managedtargetmount__host = self.host).count():
                log.error("Got no resource_locations from host %s, but there are chroma-configured mounts on that server!\n"\
                          "crm_mon returned rc=%s,stdout=%s,stderr=%s" % (self.host,
                                                                          crm_mon_error['rc'],
                                                                          crm_mon_error['stdout'],
                                                                          crm_mon_error['stderr']))
            return

        for resource_name, node_name in self.host_data['resource_locations'].items():
            try:
                target = ManagedTarget.objects.get(ha_label = resource_name)
            except ManagedTarget.DoesNotExist:
                #audit_log.warning("Resource %s on host %s is not a known target" % (resource_name, self.host))
                continue

            # If we're operating on a Managed* rather than a purely monitored target
            if not target.immutable_state:
                if node_name is None:
                    active_mount = None
                else:
                    try:
                        host = ManagedHost.objects.get(nodename = node_name)
                        try:
                            active_mount = ManagedTargetMount.objects.get(target = target, host = host)
                        except ManagedTargetMount.DoesNotExist:
                            log.warning("Resource for target '%s' is running on host '%s', but there is no such TargetMount" % (target, host))
                            active_mount = None
                    except ManagedHost.DoesNotExist:
                        log.warning("Resource location node '%s' does not match any Host" % (node_name))
                        active_mount = None

                JobSchedulerClient.notify(target, self.started_at, {
                    'state': ['unmounted', 'mounted'][active_mount != None],
                    'active_mount_id': None if active_mount is None else active_mount.id
                }, ['mounted', 'unmounted'])

    def store_lustre_target_metrics(self, target_name, metrics):
        # TODO: Re-enable MGS metrics storage if it turns out it's useful.
        if target_name == "MGS":
            return []

        try:
            target = ManagedTarget.objects.get(name=target_name,
                                        managedtargetmount__host=self.host).downcast()
        except ManagedTarget.DoesNotExist:
            # Unknown target -- ignore metrics
            log.warning("Discarding metrics for unknown target: %s" % target_name)
            return []

        return target.metrics.serialize(metrics, jobid_var=self.jobid_var)

    @transaction.commit_on_success
    def store_metrics(self):
        """
        Pass the received metrics into the metrics library for storage.
        """
        raw_metrics = self.host_data['metrics']['raw']
        self.jobid_var = raw_metrics.get('lustre', {}).get('jobid_var', 'disable')
        samples = []

        try:
            node_metrics = raw_metrics['node']
            try:
                node_metrics['lnet'] = raw_metrics['lustre']['lnet']
            except KeyError:
                pass

            samples += self.host.metrics.serialize(node_metrics)
        except KeyError:
            pass

        try:
            for target, target_metrics in raw_metrics['lustre']['target'].items():
                samples += self.store_lustre_target_metrics(target, target_metrics)
        except KeyError:
            pass

        StatsQueue().put(samples)
        return len(samples)
