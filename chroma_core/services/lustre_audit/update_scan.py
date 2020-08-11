#!/usr/bin/env python
# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import json
from itertools import chain
from chroma_core.services import log_register

from django.db import transaction
from django.db.models import Q

from chroma_core.models.target import ManagedTarget, TargetRecoveryInfo, TargetRecoveryAlert
from chroma_core.models.host import ManagedHost, VolumeNode
from chroma_core.models.client_mount import LustreClientMount
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.services.job_scheduler import job_scheduler_notify
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.models import ManagedTargetMount
from iml_common.lib.date_time import IMLDateTime
from iml_common.lib.package_version_info import VersionInfo


log = log_register(__name__)


class UpdateScan(object):
    def __init__(self):
        self.audited_mountables = {}
        self.host = None
        self.host_data = None

    def is_valid(self):
        try:
            assert isinstance(self.host_data, dict)
            assert "mounts" in self.host_data
            assert "metrics" in self.host_data
            assert "resource_locations" in self.host_data
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    def audit_host(self):
        self.update_packages(self.host_data.get("packages"))
        self.update_resource_locations()

        self.update_target_mounts()

    def run(self, host_id, host_data):
        host = ManagedHost.objects.get(pk=host_id)
        self.started_at = IMLDateTime.parse(host_data["started_at"])
        self.host = host
        self.host_data = host_data
        log.debug("UpdateScan.run: %s" % self.host)

        self.audit_host()

    # Compatibility with pre-4.1 IML upgrades
    def update_packages(self, package_report):
        if not package_report:
            # Packages is allowed to be None
            # (means is not the initial message, or there was a problem talking to RPM or yum)
            return

        # An update is required if:
        #  * A package is installed on the storage server for which there is a more recent version
        #    available on the manager
        #  or
        #  * A package is available on the manager, and specified in the server's profile's list of
        #    packages, but is not installed on the storage server.

        def _version_info_list(package_data):
            return [VersionInfo(*package) for package in package_data]

        def _updates_available(installed_versions, available_versions):
            # versions are of form (EPOCH, VERSION, RELEASE, ARCH)

            # Map of arch to highest installed version
            max_installed_version = {}

            for installed_info in installed_versions:
                max_inst = max_installed_version.get(installed_info.arch, None)
                if max_inst is None or installed_info > max_inst:
                    max_installed_version[installed_info.arch] = installed_info

            for available_info in available_versions:
                max_inst = max_installed_version.get(available_info.arch, None)
                if max_inst is not None and available_info > max_inst:
                    log.debug("Update available: %s > %s" % (available_info, max_inst))
                    return True

            return False

        updates = False

        repos = package_report.keys()
        for package_name in set(chain(self.host.server_profile.base_packages, self.host.server_profile.packages)):
            package_data = {}
            for repo in repos:
                try:
                    package_data = package_report[repo][package_name]
                except KeyError:
                    continue
                break

            if not package_data:
                log.warning("Required Package %s not available for %s" % (package_name, self.host))
                continue

            if not package_data["installed"]:
                log.info("Update available (not installed): %s on %s" % (package_name, self.host))
                updates = True
                break

            if _updates_available(
                _version_info_list(package_data["installed"]), _version_info_list(package_data["available"])
            ):
                log.info("Update needed: %s on %s" % (package_name, self.host))
                updates = True
                break

        log.info("update_packages(%s): updates=%s" % (self.host, updates))
        job_scheduler_notify.notify(self.host, self.started_at, {"needs_update": updates})

    def update_target_mounts(self):
        # If mounts is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no mounts
        if self.host_data["mounts"] is None:
            return

        # Loop over all mountables we expected on this host, whether they
        # were actually seen in the results or not.
        mounted_uuids = dict([(str(m["fs_uuid"]), m) for m in self.host_data["mounts"]])
        for target_mount in ManagedTargetMount.objects.filter(host=self.host):

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
                    job_scheduler_notify.notify(
                        target,
                        self.started_at,
                        {"state": "mounted", "active_mount_id": target_mount.id},
                        ["mounted", "unmounted"],
                    )
                elif not mounted_locally and target.active_mount == target_mount:
                    log.debug("clearing active_mount, %s %s", self.started_at, self.host)

                    job_scheduler_notify.notify(
                        target,
                        self.started_at,
                        {"state": "unmounted", "active_mount_id": None},
                        ["mounted", "unmounted"],
                    )

            with transaction.atomic():
                if target_mount.target.active_mount is None:
                    TargetRecoveryInfo.update(target_mount.target, {})
                    TargetRecoveryAlert.notify(target_mount.target, False)
                elif mounted_locally:
                    recovering = TargetRecoveryInfo.update(target_mount.target, recovery_status)
                    TargetRecoveryAlert.notify(target_mount.target, recovering)

    def update_resource_locations(self):
        # If resource_locations is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no resource_locations
        if self.host_data["resource_locations"] is None:
            return

        if "crm_mon_error" in self.host_data["resource_locations"]:
            # Means that it was not possible to obtain a
            # list from corosync: corosync may well be absent if
            # we're monitoring a non-chroma-managed monitor-only
            # system.  But if there are managed mounts
            # then this is a problem.
            crm_mon_error = self.host_data["resource_locations"]["crm_mon_error"]
            if ManagedTarget.objects.filter(immutable_state=False, managedtargetmount__host=self.host).count():
                log.error(
                    "Got no resource_locations from host %s, but there are chroma-configured mounts on that server!\n"
                    "crm_mon returned rc=%s,stdout=%s,stderr=%s"
                    % (self.host, crm_mon_error["rc"], crm_mon_error["stdout"], crm_mon_error["stderr"])
                )
            return

        for resource_name, node_name in self.host_data["resource_locations"].items():
            try:
                target = ManagedTarget.objects.get(ha_label=resource_name)
            except ManagedTarget.DoesNotExist:
                # audit_log.warning("Resource %s on host %s is not a known target" % (resource_name, self.host))
                continue

            # If we're operating on a Managed* rather than a purely monitored target
            if not target.immutable_state:
                if node_name is None:
                    active_mount = None
                else:
                    try:
                        host = ManagedHost.objects.get(Q(nodename=node_name) | Q(fqdn=node_name))
                        try:
                            active_mount = ManagedTargetMount.objects.get(target=target, host=host)
                        except ManagedTargetMount.DoesNotExist:
                            log.warning(
                                "Resource for target '%s' is running on host '%s', but there is no such TargetMount"
                                % (target, host)
                            )
                            active_mount = None
                    except ManagedHost.DoesNotExist:
                        log.warning("Resource location node '%s' does not match any Host" % (node_name))
                        active_mount = None

                job_scheduler_notify.notify(
                    target,
                    self.started_at,
                    {
                        "state": ["unmounted", "mounted"][active_mount is not None],
                        "active_mount_id": None if active_mount is None else active_mount.id,
                    },
                    ["mounted", "unmounted"],
                )
