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
    Authorization tokens handed out to servers to grant them
    the right to register themselves with the manager.
    """
    name = models.CharField(
        primary_key=True,
        max_length = 50,
        help_text = "String, server profile identifier")
    ui_name = models.CharField(
        max_length = 50,
        help_text = "String, the name of the server profile")
    ui_description = models.TextField(help_text = "Description of the server profile")
    managed = models.BooleanField(
        default=True,
        help_text = "Boolean, if the server will be managed"
    )
    bundles = models.ManyToManyField(
        Bundle,
        help_text = "The bundles specified by this profile"
    )

    @property
    def id(self):
        """
        Work around tastypie bug, when calling get_resource_uri it looks for .id
        """
        return self.pk

    # TODO: add a 'default' flag so that we can consistently
    # present a default in the UI

    class Meta:
        app_label = 'chroma_core'
        unique_together = ('name',)
