# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from django.db import models
from django.contrib.postgres.fields import ArrayField


class Device(models.Model):
    id = models.CharField(primary_key=True, help_text="Unique identifer per-device", max_length=255)
    size = models.CharField(help_text="The size of the device in bytes", max_length=64)
    usable_for_lustre = models.BooleanField(help_text="Is this storage device usable for Lustre")
    device_type = models.CharField(help_text="The type of block or virtual device", max_length=64)
    parents = ArrayField(models.CharField(max_length=255), help_text="A list of parent devices")
    children = ArrayField(models.CharField(max_length=255), help_text="A list of child devices")
    max_depth = models.SmallIntegerField(help_text="Maximum depth where the device is nested")
    record_id = models.IntegerField(help_text="Integer id for cache in warp-drive to use", null=True)


class DeviceHost(models.Model):
    device_id = models.CharField(help_text="Unique identifer per-device", max_length=255)
    fqdn = models.CharField(help_text="The fqdn this device may reside on", max_length=255)
    local = models.BooleanField(help_text="Is the device local to this node")
    paths = ArrayField(models.CharField(max_length=255), help_text="A list of paths to access a device")
    mount_path = models.CharField(null=True, help_text="The mounted path of the device", max_length=255)
    fs_type = models.CharField(null=True, help_text="The fs type of the device", max_length=255)
    fs_label = models.CharField(null=True, help_text="The fs label on the device", max_length=255)
    fs_uuid = models.CharField(null=True, help_text="The fs uuid on the device", max_length=255)
