#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


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
