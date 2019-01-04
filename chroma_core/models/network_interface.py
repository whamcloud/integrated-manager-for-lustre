# -*- coding: utf-8 -*-
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from django.db import models

from chroma_core.models import Nid


class NetworkInterface(models.Model):
    host = models.ForeignKey("ManagedHost")

    name = models.CharField(max_length=32)
    inet4_address = models.CharField(max_length=128)
    inet4_prefix = models.IntegerField()
    corosync_configuration = models.ForeignKey("CorosyncConfiguration", null=True)
    type = models.CharField(max_length=32)  # tcp, o2ib, ... (best stick to lnet types!)
    state_up = models.BooleanField()

    def __str__(self):
        return "%s-%s" % (self.host, self.name)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]
        unique_together = ("host", "name")

    @property
    def lnd_types(self):
        return Nid.lnd_types_for_network_type(self.type)
