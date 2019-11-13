# -*- coding: utf-8 -*-
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models
from django.db.models import CASCADE


class ClientCertificate(models.Model):
    host = models.ForeignKey("ManagedHost", on_delete=CASCADE)
    serial = models.CharField(max_length=16)
    revoked = models.BooleanField(default=False)

    class Meta:
        app_label = "chroma_core"
