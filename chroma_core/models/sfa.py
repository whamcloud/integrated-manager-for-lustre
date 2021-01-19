# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from django.db import models
from django.db.models import CASCADE


class SfaStorageSystem(models.Model):
    class Meta:
        app_label = "chroma_core"

    uuid = models.TextField(
        unique=True,
    )
    platform = models.TextField()
    health_state_reason = models.TextField()
    health_state = models.PositiveSmallIntegerField()
    child_health_state = models.PositiveSmallIntegerField()


class SfaEnclosure(models.Model):
    class Meta:
        app_label = "chroma_core"
        unique_together = (("index", "storage_system"),)

    index = models.PositiveIntegerField()
    element_name = models.TextField()
    health_state = models.PositiveSmallIntegerField()
    health_state_reason = models.TextField()
    child_health_state = models.PositiveSmallIntegerField()
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
        unique_together = (("enclosure_index", "disk_drive_index", "storage_system"),)

    index = models.PositiveIntegerField()
    enclosure_index = models.PositiveIntegerField()
    disk_drive_index = models.PositiveIntegerField()
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )


class SfaDiskDrive(models.Model):
    class Meta:
        app_label = "chroma_core"
        unique_together = (("index", "storage_system"),)

    index = models.PositiveIntegerField()
    enclosure_index = models.PositiveIntegerField()
    failed = models.BooleanField(null=False)
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
        unique_together = (("index", "storage_system"),)

    index = models.PositiveIntegerField()
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
        unique_together = (("index", "storage_system", "enclosure_index"),)

    index = models.PositiveIntegerField()
    enclosure_index = models.PositiveIntegerField()
    health_state = models.PositiveSmallIntegerField()
    health_state_reason = models.TextField()
    position = models.PositiveSmallIntegerField()
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )


class SfaController(models.Model):
    class Meta:
        app_label = "chroma_core"
        unique_together = (("index", "storage_system"),)

    index = models.PositiveIntegerField()
    enclosure_index = models.PositiveIntegerField()
    health_state = models.PositiveSmallIntegerField()
    health_state_reason = models.TextField()
    child_health_state = models.PositiveSmallIntegerField()
    storage_system = models.ForeignKey(
        "SfaStorageSystem", to_field="uuid", db_column="storage_system", on_delete=CASCADE
    )
