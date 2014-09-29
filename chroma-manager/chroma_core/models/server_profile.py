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


from django.db import models
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
        default=True,
        help_text = "Boolean, if the host will be managed"
    )
    worker = models.BooleanField(
        default = False,
        help_text = "Boolean, if the host is available to be used as a Lustre worker node"
    )
    bundles = models.ManyToManyField(
        Bundle,
        help_text = "The bundles specified by this profile"
    )
    user_selectable = models.BooleanField(default=True)
    initial_state = models.CharField(max_length=32, default='configured')

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
