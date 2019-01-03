#!/usr/bin/env python
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import json
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
from chroma_core.services.stats import StatsQueue


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

    @transaction.commit_on_success
    def audit_host(self):
        self.update_properties(self.host_data.get("properties"))
        self.update_packages(self.host_data.get("packages"))
        self.update_resource_locations()
        self.update_target_mounts()
        self.update_client_mounts()

    def run(self, host_id, host_data):
        host = ManagedHost.objects.get(pk=host_id)
        self.started_at = IMLDateTime.parse(host_data["started_at"])
        self.host = host
        self.host_data = host_data
        log.debug("UpdateScan.run: %s" % self.host)

        self.audit_host()
        self.store_metrics()

    def update_properties(self, properties):
        if properties is not None:
            properties = json.dumps(properties)
            # use the job scheduler to update, but only as necessary
            if self.host.properties != properties:
                job_scheduler_notify.notify(self.host, self.started_at, {"properties": properties})

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
        for package in self.host.server_profile.serverprofilepackage_set.all():
            package_data = {}
            for repo in repos:
                try:
                    package_data = package_report[repo][package.package_name]
                except KeyError:
                    continue
                break

            if not package_data:
                log.warning("Required Package %s not available for %s" % (package.package_name, self.host))
                continue

            if not package_data["installed"]:
                log.info("Update available (not installed): %s on %s" % (package.package_name, self.host))
                updates = True
                break

            if _updates_available(
                _version_info_list(package_data["installed"]), _version_info_list(package_data["available"])
            ):
                log.info("Update needed: %s on %s" % (package.package_name, self.host))
                updates = True
                break

        log.info("update_packages(%s): updates=%s" % (self.host, updates))
        job_scheduler_notify.notify(self.host, self.started_at, {"needs_update": updates})

    def update_client_mounts(self):
        # Client mount audit comes in via metrics due to the way the
        # ClientAudit is implemented.
        try:
            client_mounts = self.host_data["metrics"]["raw"]["lustre_client_mounts"]
        except KeyError:
            client_mounts = []

        # If lustre_client_mounts is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no mounts
        if client_mounts == None:
            return

        expected_fs_mounts = LustreClientMount.objects.select_related("filesystem").filter(host=self.host)
        actual_fs_mounts = [m["mountspec"].split(":/")[1] for m in client_mounts]

        # Don't bother with the rest if there's nothing to do.
        if len(expected_fs_mounts) == 0 and len(actual_fs_mounts) == 0:
            return

        for expected_mount in expected_fs_mounts:
            if expected_mount.active and expected_mount.filesystem.name not in actual_fs_mounts:
                update = dict(state="unmounted", mountpoint=None)
                job_scheduler_notify.notify(expected_mount, self.started_at, update)
                log.info("updated mount %s on %s -> inactive" % (expected_mount.mountpoint, self.host))

        for actual_mount in client_mounts:
            fsname = actual_mount["mountspec"].split(":/")[1]
            try:
                mount = [m for m in expected_fs_mounts if m.filesystem.name == fsname][0]
                log.debug("mount: %s" % mount)
                if not mount.active:
                    update = dict(state="mounted", mountpoint=actual_mount["mountpoint"])
                    job_scheduler_notify.notify(mount, self.started_at, update)
                    log.info("updated mount %s on %s -> active" % (actual_mount["mountpoint"], self.host))
            except IndexError:
                log.info("creating new mount %s on %s" % (actual_mount["mountpoint"], self.host))
                filesystem = ManagedFilesystem.objects.get(name=fsname)
                JobSchedulerClient.create_client_mount(self.host, filesystem, actual_mount["mountpoint"])

    def update_target_mounts(self):
        # If mounts is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no mounts
        if self.host_data["mounts"] == None:
            return

        # Loop over all mountables we expected on this host, whether they
        # were actually seen in the results or not.
        mounted_uuids = dict([(m["fs_uuid"], m) for m in self.host_data["mounts"]])
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

            if target_mount.target.active_mount == None:
                TargetRecoveryInfo.update(target_mount.target, {})
                TargetRecoveryAlert.notify(target_mount.target, False)
            elif mounted_locally:
                recovering = TargetRecoveryInfo.update(target_mount.target, recovery_status)
                TargetRecoveryAlert.notify(target_mount.target, recovering)

    def update_resource_locations(self):
        # If resource_locations is None then nothing changed since the last update and so we can just return.
        # Not the same as [] empty list which means no resource_locations
        if self.host_data["resource_locations"] == None:
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
                        "state": ["unmounted", "mounted"][active_mount != None],
                        "active_mount_id": None if active_mount is None else active_mount.id,
                    },
                    ["mounted", "unmounted"],
                )

    def store_lustre_target_metrics(self, target_name, metrics):
        # TODO: Re-enable MGS metrics storage if it turns out it's useful.
        if target_name == "MGS":
            return []

        try:
            target = ManagedTarget.objects.get(name=target_name).downcast()

            if target.immutable_state:
                # in monitored mode we want to make sure the target volume is accessible on current host
                target.volume.volumenode_set.get(host=self.host, not_deleted=True)
            else:
                target.managedtargetmount_set.get(host=self.host, not_deleted=True)
        except (ManagedTarget.DoesNotExist, VolumeNode.DoesNotExist) as e:
            # Unknown target -- ignore metrics
            log.warning("Discarding metrics for unknown target: %s (%s)" % (target_name, e))
            return []

        return target.metrics.serialize(metrics, jobid_var=self.jobid_var)

    @transaction.commit_on_success
    def store_metrics(self):
        """
        Pass the received metrics into the metrics library for storage.
        """
        raw_metrics = self.host_data["metrics"]["raw"]
        self.jobid_var = raw_metrics.get("lustre", {}).get("jobid_var", "disable")
        samples = []

        try:
            node_metrics = raw_metrics["node"]
            try:
                node_metrics["lnet"] = raw_metrics["lustre"]["lnet"]
            except KeyError:
                pass

            samples += self.host.metrics.serialize(node_metrics)
        except KeyError:
            pass

        try:
            for target, target_metrics in raw_metrics["lustre"]["target"].items():
                samples += self.store_lustre_target_metrics(target, target_metrics)
        except KeyError:
            pass

        StatsQueue().put(samples)
        return len(samples)
