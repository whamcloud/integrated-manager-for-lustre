# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models
from django.db import IntegrityError
from django.utils import timezone

from chroma_core.models.bundle import Bundle


class ServerProfile(models.Model):
    """
    Server profiles specify a set of configuration options to be applied to a storage server,
    in particular which bundles and packages are installed.
    """
    name = models.CharField(
        primary_key=True,
        max_length = 50,
        help_text = "String, unique name")
    ui_name = models.CharField(
        max_length = 50,
        help_text = "String, human readable name")
    ui_description = models.TextField(help_text = "Description of the server profile")
    managed = models.BooleanField(
        help_text = "Boolean, True if the host will be managed"
    )
    worker = models.BooleanField(
        help_text = "Boolean, True if the host is available to be used as a Lustre worker node"
    )
    bundles = models.ManyToManyField(
        Bundle,
        help_text = "The bundles specified by this profile"
    )
    user_selectable = models.BooleanField(default=True)
    initial_state = models.CharField(max_length=32)
    rsyslog = models.BooleanField(
        help_text = "Boolean, True if the host will manage rsyslog"
    )
    ntp = models.BooleanField(
        help_text = "Boolean, True if the host will manage ntp"
    )
    corosync = models.BooleanField(
        help_text = "Boolean, True if the host will manage corosync"
    )
    corosync2 = models.BooleanField(
        help_text = "Boolean, True if the host will manage corosync2"
    )
    pacemaker = models.BooleanField(
        help_text = "Boolean, True if the host will manage pacemaker"
    )
    modified_at = models.DateTimeField(default=timezone.now, blank=True)

    @property
    def packages(self):
        """
        Convenience for obtaining an iterable of package names from the ServerProfilePackage model
        """
        for package in self.serverprofilepackage_set.all().values('package_name'):
            yield package['package_name']

    default = models.BooleanField(default=False,
                                  help_text="If True, this profile is presented as the default when adding"
                                            "storage servers")

    @property
    def id(self):
        """
        Work around tastypie bug, when calling get_resource_uri it looks for .id
        """
        return self.pk

    @property
    def as_dict(self):
        result = {}

        for field in self._meta.fields:
            result[field.name] = getattr(self, field.name)

        return result

    def save(self, *args, **kwargs):
        """
        Quick validation before saving
        """
        if self.corosync and self.corosync2:
            raise IntegrityError("Corosync and Corosync2 configured for %s" % self.name)

        super(ServerProfile, self).save(*args, **kwargs)

    class Meta:
        app_label = 'chroma_core'
        unique_together = (('name',))


class ServerProfilePackage(models.Model):
    """
    Represents the 'packages' attribute of a server profile JSON specification.

    Each server profile has a set of ServerProfilePackage records identifying
    which packages should be installed on servers using this profile.
    """
    class Meta:
        app_label = 'chroma_core'
        unique_together = ('bundle', 'server_profile', 'package_name')

    bundle = models.ForeignKey(Bundle)
    server_profile = models.ForeignKey(ServerProfile)
    package_name = models.CharField(max_length=255)
    modified_at = models.DateTimeField(default=timezone.now, blank=True)


class ServerProfileValidation(models.Model):
    """
    Represents a validation that must be true for the profile to be installed on a server.
    Each server profile has a set of ServerProfileValidation records identifying a set
    of validation attributes that must be true.
    For example a profile might have the following
    test=> "zfs_installed == False"  description=> "ZFS must not be installed"
    test=> "distro == 'rhel'"        description=> "RHEL is the only support distribution"
    test=> "memory_gb >= 32"         description=> "32GB of memory is required"

    test is the python expression that must evaluate to true for the profile to be valid
    description is the user information that can be viewed in the GUI
    """
    class Meta:
        app_label = 'chroma_core'

    server_profile = models.ForeignKey(ServerProfile)
    test = models.CharField(max_length=256)
    description = models.CharField(max_length=256)
    modified_at = models.DateTimeField(default=timezone.now, blank=True)
