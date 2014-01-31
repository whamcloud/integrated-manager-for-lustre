#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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
        help_text = "Boolean, if the server will be managed"
    )
    worker = models.BooleanField(
        default = False,
        help_text = "Boolean, if the server is available to be used as a Lustre worker node"
    )
    bundles = models.ManyToManyField(
        Bundle,
        help_text = "The bundles specified by this profile"
    )

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
