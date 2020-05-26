# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from django.db import models
from django.db.models import CASCADE


class SfaStorageSystem(models.Model):
    class Meta:
        app_label = "chroma_core"

    uuid = models.TextField(unique=True,)
    health_state_reason = models.TextField()
    health_state = models.PositiveSmallIntegerField()
    child_health_state = models.PositiveSmallIntegerField()


class SfaEnclosure(models.Model):
    class Meta:
        app_label = "chroma_core"

    index = models.PositiveIntegerField(unique=True, primary_key=True)
    element_name = models.TextField()
    health_state = models.PositiveSmallIntegerField()
    health_state_reason = models.TextField()
    model = models.TextField()
    position = models.PositiveSmallIntegerField()
    enclosure_type = models.PositiveSmallIntegerField()
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )
    canister_location = models.TextField()


class SFADiskSlot(models.Model):
    class Meta:
        app_label = "chroma_core"
        unique_together = (("enclosure_index", "disk_drive_index"),)

    index = models.PositiveIntegerField(unique=True, primary_key=True)
    enclosure_index = models.ForeignKey(
        "SfaEnclosure", to_field="index", db_column="enclosure_index", on_delete=CASCADE
    )
    disk_drive_index = models.ForeignKey(
        "SfaDiskDrive", to_field="index", db_column="disk_drive_index", on_delete=CASCADE
    )
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )


class SfaDiskDrive(models.Model):
    class Meta:
        app_label = "chroma_core"

    index = models.PositiveIntegerField(unique=True, primary_key=True)
    child_health_state = models.PositiveSmallIntegerField()
    enclosure_index = models.ForeignKey(
        "SfaEnclosure", to_field="index", db_column="enclosure_index", on_delete=CASCADE
    )
    failed = models.BooleanField(null=False)
    health_state_reason = models.TextField()
    slot_number = models.PositiveIntegerField()
    health_state = models.PositiveSmallIntegerField()
    health_state_reason = models.TextField()
    member_index = models.PositiveSmallIntegerField(null=True)
    member_state = models.PositiveSmallIntegerField()
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )


class SfaJob(models.Model):
    class Meta:
        app_label = "chroma_core"

    index = models.PositiveIntegerField(unique=True, primary_key=True)
    sub_target_index = models.PositiveIntegerField(null=True)
    sub_target_type = models.PositiveSmallIntegerField(null=True)
    job_type = models.PositiveSmallIntegerField()
    state = models.PositiveSmallIntegerField()
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )


class SfaPowerSupply(models.Model):
    class Meta:
        app_label = "chroma_core"

    index = models.PositiveIntegerField(unique=True, primary_key=True)
    enclosure_index = models.ForeignKey(
        "SfaEnclosure", to_field="index", db_column="enclosure_index", on_delete=CASCADE
    )
    health_state = models.PositiveSmallIntegerField()
    health_state_reason = models.TextField()
    position = models.PositiveSmallIntegerField()
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )
