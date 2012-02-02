
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from monitor.models import DeletableMetaclass


class ManagedTargetMount(models.Model):
    """Associate a particular Lustre target with a device node on a host"""
    __metaclass__ = DeletableMetaclass

    # FIXME: both LunNode and TargetMount refer to the host
    host = models.ForeignKey('ManagedHost')
    mount_point = models.CharField(max_length = 512, null = True, blank = True)
    block_device = models.ForeignKey('LunNode')
    primary = models.BooleanField()
    target = models.ForeignKey('ManagedTarget')

    def save(self, force_insert = False, force_update = False, using = None):
        # If primary is true, then target must be unique
        if self.primary:
            from django.db.models import Q
            other_primaries = ManagedTargetMount.objects.filter(~Q(id = self.id), target = self.target, primary = True)
            if other_primaries.count() > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple primary mounts for target %s" % self.target)

        # If this is an MGS, there may not be another MGS on
        # this host
        from configure.models.target import ManagedMgs
        if isinstance(self.target.downcast(), ManagedMgs):
            from django.db.models import Q
            other_mgs_mountables_local = ManagedTargetMount.objects.filter(~Q(id = self.id), target__in = ManagedMgs.objects.all(), host = self.host).count()
            if other_mgs_mountables_local > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple MGS mounts on host %s" % self.host.address)

        return super(ManagedTargetMount, self).save(force_insert, force_update, using)

    def device(self):
        return self.block_device.path

    def status_string(self):
        from monitor.models import TargetRecoveryAlert
        in_recovery = (TargetRecoveryAlert.filter_by_item(self.target).count() > 0)
        if self.target.active_mount == self:
            if in_recovery:
                return "RECOVERY"
            elif self.primary:
                return "STARTED"
            else:
                return "FAILOVER"
        else:
            if self.primary:
                return "OFFLINE"
            else:
                return "SPARE"

    def pretty_block_device(self):
        # Truncate to iSCSI iqn if possible
        parts = self.block_device.path.split("-iscsi-")
        if len(parts) == 2:
            return parts[1]

        # Strip /dev/mapper if possible
        parts = self.block_device.path.split("/dev/mapper/")
        if len(parts) == 2:
            return parts[1]

        # Strip /dev if possible
        parts = self.block_device.path.split("/dev/")
        if len(parts) == 2:
            return parts[1]

        # Fall through, do nothing
        return self.block_device

    class Meta:
        app_label = 'configure'

    def __str__(self):
        if self.primary:
            kind_string = "primary"
        elif not self.block_device:
            kind_string = "failover_nodev"
        else:
            kind_string = "failover"

        return "%s:%s:%s" % (self.host, kind_string, self.target)
