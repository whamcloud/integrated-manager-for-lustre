# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models
from django.utils import timezone


class Bundle(models.Model):
    modified_at = models.DateTimeField(default=timezone.now, blank=True)                                   
    bundle_name = models.CharField(primary_key = True, max_length = 50,
                                   help_text = "Unicode string, bundle name")
    version = models.CharField(max_length = 255, default = "0.0.0",
                               help_text = "Unicode string, bundle version")
    location = models.CharField(max_length = 255,
                                help_text = "Unicode string, bundle location")
    description = models.CharField(max_length = 255,
                                   help_text = "Unicode string, bundle description")

    class Meta:
        unique_together = ('bundle_name',)
        app_label = 'chroma_core'
