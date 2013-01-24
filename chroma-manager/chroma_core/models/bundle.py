#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db import models


class Bundle(models.Model):
    bundle_name = models.CharField(primary_key = True, max_length = 50,
                                   help_text = "Unicode string, bundle name")
    location = models.CharField(max_length = 255,
                                help_text = "Unicode string, bundle location")
    description = models.CharField(max_length = 255,
                                   help_text = "Unicode string, bundle description")

    class Meta:
        unique_together = ('bundle_name',)
        app_label = 'chroma_core'
