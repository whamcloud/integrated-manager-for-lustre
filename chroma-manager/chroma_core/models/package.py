# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models
from django.db.models import CharField, ForeignKey, IntegerField
from django.utils import timezone

from chroma_core.services import log_register
from iml_common.lib.package_version_info import VersionInfo

log = log_register('package_update')


class Package(models.Model):
    class Meta:
        app_label = 'chroma_core'

    modified_at = models.DateTimeField(default=timezone.now, blank=True, editable=False)
    name = CharField(max_length=128, unique=True)


class PackageVersion(models.Model):
    class Meta:
        app_label = 'chroma_core'
        unique_together = ('package', 'version', 'release')

    package = ForeignKey('Package')
    epoch = IntegerField()
    version = CharField(max_length=128)
    release = CharField(max_length=128)
    arch = CharField(max_length=32)
    modified_at = models.DateTimeField(default=timezone.now, blank=True, editable=False)


class PackageInstallation(models.Model):
    class Meta:
        app_label = 'chroma_core'
        unique_together = ('package_version', 'host')


    package_version = ForeignKey('PackageVersion')
    host = ForeignKey('ManagedHost')
    modified_at = models.DateTimeField(default=timezone.now, blank=True, editable=False)


class PackageAvailability(models.Model):
    class Meta:
        app_label = 'chroma_core'
        unique_together = ('package_version', 'host')

    package_version = ForeignKey('PackageVersion')
    host = ForeignKey('ManagedHost')
    modified_at = models.DateTimeField(default=timezone.now, blank=True, editable=False)


def update(host, package_report):
    """
    Update the Package, PackageVersion, PackageInstallation and PackageAvailability models
    according to a report from a storage server.

    :return: True if updates are available, else False
    """
    updates = False

    installed_ids = []
    available_ids = []

    def _updates_available(installed_versions, available_versions):
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

    def _version_info_list(package_data):
        return [VersionInfo(*package) for package in package_data]

    repo_names = set(host.server_profile.bundles.values_list('bundle_name', flat=True))
    for repo_name in repo_names.intersection(package_report):
        for package_name, package_data in package_report[repo_name].items():
            for version_info in _version_info_list(package_data['installed']):
                package, created = Package.objects.get_or_create(name=package_name)
                package_version, created = PackageVersion.objects.get_or_create(
                    package=package, epoch=version_info.epoch, version=version_info.version,
                    release=version_info.release, arch=version_info.arch)
                installed_package, created = PackageInstallation.objects.get_or_create(
                    package_version=package_version,
                    host=host)
                installed_ids.append(installed_package.id)

            for version_info in _version_info_list(package_data['available']):
                package, created = Package.objects.get_or_create(name=package_name)
                package_version, created = PackageVersion.objects.get_or_create(
                    package=package, epoch=version_info.epoch, version=version_info.version,
                    release=version_info.release, arch=version_info.arch)
                available_package, created = PackageAvailability.objects.get_or_create(
                    package_version=package_version,
                    host=host)
                available_ids.append(available_package.id)

            # Are there any installed packages from this bundle with updates available?
            updates = updates or _updates_available(_version_info_list(
                package_data['installed']), _version_info_list(package_data['available']))

    # Remove any old package records
    PackageInstallation.objects.exclude(id__in=installed_ids).filter(host=host).delete()
    PackageAvailability.objects.exclude(id__in=available_ids).filter(host=host).delete()
    PackageVersion.objects.filter(packageinstallation=None, packageavailability=None).delete()
    Package.objects.filter(packageversion=None).delete()

    return updates
