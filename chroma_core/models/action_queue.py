# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from django.db import models
from django.db.models import CASCADE
from django.contrib.postgres.fields import ArrayField, JSONField

from chroma_core.lib.job import DependOn, DependAll, Step, job_log
from chroma_core.models import ManagedFilesystem


class LustreFidField(models.Field):
    description = "A Lustre FID"

    seq = models.BigIntegerField()
    oid = models.IntegerField()
    ver = models.IntegerField()

    def db_type(self, connection):
        return "lustre_fid"

    class Meta:
        app_label = "chroma_core"


class Mailbox(models.Model):
    """ List of deliveries for action queues """

    class Meta:
        app_label = "chroma_core"

    filesystem = models.ForeignKey("ManagedFilesystem", on_delete=CASCADE)

    name = models.CharField(max_length=128)
    start = models.DateTimeField()
    finish = models.DateTimeField()

    state = models.CharField(max_length=16)

    fids_total = models.BigIntegerField(default=0)
    fids_completed = models.BigIntegerField(default=0)
    fids_failed = models.BigIntegerField(default=0)
    data_transfered = models.BigIntegerField(default=0)

    keep_failed = models.BooleanField(default=True, null=False)
    # Actually links to ActionType
    actions = ArrayField(models.CharField(max_length=16))

    args = JSONField(default={})


class FidActionQueue(models.Model):
    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        app_label = "chroma_core"

    fid = LustreFidField()

    mailbox = models.ForeignKey("Mailboxes", on_delete=CASCADE)

    data = JSONField(default={})
    failed = models.PositiveSmallIntegerField(default=0, null=False)
