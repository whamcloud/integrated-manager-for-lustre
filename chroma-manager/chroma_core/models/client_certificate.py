# -*- coding: utf-8 -*-
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models
from django.utils import timezone


class ClientCertificate(models.Model):
    modified_at = models.DateTimeField(default=timezone.now, blank=True)                                   
    host = models.ForeignKey('ManagedHost')
    serial = models.CharField(max_length = 16)
    revoked = models.BooleanField(default = False)

    class Meta:
        app_label = 'chroma_core'
