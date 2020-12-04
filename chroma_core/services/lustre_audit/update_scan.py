#!/usr/bin/env python
# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from itertools import chain
from chroma_core.services import log_register
from chroma_core.models.host import ManagedHost
from chroma_core.services.job_scheduler import job_scheduler_notify
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
