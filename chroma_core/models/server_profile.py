# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models
from django.db.models import CASCADE
from django.db import IntegrityError

from chroma_core.models.repo import Repo


class ServerProfile(models.Model):
    """
    Server profiles specify a set of configuration options to be applied to a storage server,
    in particular which repos and packages are installed.
    """

    name = models.CharField(primary_key=True, max_length=50, help_text="String, unique name")
    ui_name = models.CharField(max_length=50, help_text="String, human readable name")
    ui_description = models.TextField(help_text="Description of the server profile")
    managed = models.BooleanField(help_text="Boolean, True if the host will be managed")
    worker = models.BooleanField(
        default=False, help_text="Boolean, True if the host is available to be used as a Lustre worker node"
    )
    repolist = models.ManyToManyField(Repo, help_text="The repolist specified by this profile")
    user_selectable = models.BooleanField(default=True)
    initial_state = models.CharField(max_length=32)
    ntp = models.BooleanField(default=False, help_text="Boolean, True if the host will manage ntp")
    corosync = models.BooleanField(default=False, help_text="Boolean, True if the host will manage corosync")
    corosync2 = models.BooleanField(default=False, help_text="Boolean, True if the host will manage corosync2")
    pacemaker = models.BooleanField(default=False, help_text="Boolean, True if the host will manage pacemaker")

    @property
    def packages(self):
        """
        Convenience for obtaining an iterable of package names from the ServerProfilePackage model
        """
        for package in self.serverprofilepackage_set.all().values("package_name"):
            yield package["package_name"]

    @property
    def base_packages(self):
        """
        Obtaining an iterable list of the base packages always installed on a host
        """
        for package in ["python2-iml-agent", "rust-iml-agent"]:
            yield package

    @property
    def repos(self):
        """
        Convenience for obtaining an iterable of repo names from the ServerProfilePackage model
        """
        for repo in self.repolist.all():
            yield repo.repo_name

    default = models.BooleanField(
        default=False, help_text="If True, this profile is presented as the default when adding" "storage servers"
    )

    @property
    def repo_contents(self):
        """
        Convenience for obtaining the merged contents of the repo file.
        """
        return "".join(repo.contents for repo in self.repolist.all())

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
        result["packages"] = list(self.packages)

        return result

    def save(self, *args, **kwargs):
        """
        Quick validation before saving
        """
        if self.corosync and self.corosync2:
            raise IntegrityError("Corosync and Corosync2 configured for %s" % self.name)

        super(ServerProfile, self).save(*args, **kwargs)

    class Meta:
        app_label = "chroma_core"
        unique_together = ("name",)


class ServerProfilePackage(models.Model):
    """
    Represents the 'packages' attribute of a server profile JSON specification.

    Each server profile has a set of ServerProfilePackage records identifying
    which packages should be installed on servers using this profile.
    """

    class Meta:
        app_label = "chroma_core"
        unique_together = ("server_profile", "package_name")

    server_profile = models.ForeignKey(ServerProfile, on_delete=CASCADE)
    package_name = models.CharField(max_length=255)


class ServerProfileValidation(models.Model):
    """
    Represents a validation that must be true for the profile to be installed on a server.
    Each server profile has a set of ServerProfileValidation records identifying a set
    of validation attributes that must be true.
    For example a profile might have the following
    test=> "distro == 'rhel'"        description=> "RHEL is the only support distribution"
    test=> "memory_gb >= 32"         description=> "32GB of memory is required"

    test is the python expression that must evaluate to true for the profile to be valid
    description is the user information that can be viewed in the GUI
    """

    class Meta:
        app_label = "chroma_core"

    server_profile = models.ForeignKey(ServerProfile, on_delete=CASCADE)
    test = models.CharField(max_length=256)
    description = models.CharField(max_length=256)
