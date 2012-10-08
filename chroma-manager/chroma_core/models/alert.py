#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db import models
from polymorphic.models import DowncastMetaclass
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.utils.timezone import now as django_now


class AlertState(models.Model):
    """Records a period of time during which a particular
       issue affected a particular element of the system"""
    __metaclass__ = DowncastMetaclass

    alert_item_type = models.ForeignKey(ContentType, related_name='alertstate_alert_item_type')
    alert_item_id = models.PositiveIntegerField()
    # FIXME: generic foreign key does not automatically set up deletion
    # of this when the alert_item is deleted -- do it manually
    alert_item = GenericForeignKey('alert_item_type', 'alert_item_id')

    alert_type = models.CharField(max_length = 128)

    begin = models.DateTimeField(help_text = "Time at which the alert started")
    end = models.DateTimeField(help_text = "Time at which the alert was resolved\
            if active is false, else time that the alert was last checked (e.g.\
            time when we last checked an offline target was still not offline)")

    # Note: use True and None instead of True and False so that
    # unique-together constraint only applied to active alerts
    active = models.NullBooleanField()

    # whether a user has manually dismissed alert
    dismissed = models.BooleanField()

    def to_dict(self):
        from chroma_core.lib.util import time_str
        return {
         # FIXME: retire misnamed 'alert_created_at'
         'alert_created_at': self.begin,
         'alert_created_at_short': self.begin,
         'begin': self.begin,
         'end': self.end,
         'alert_severity': 'alert',  # FIXME: Still need to figure out wheather to pass enum or display string.
         'alert_item': str(self.alert_item),
         'alert_message': self.message(),
         'message': self.message(),
         'active': bool(self.active),
         'begin': time_str(self.begin),
         'end': time_str(self.end),
         'id': self.id,
         'alert_item_id': self.alert_item_id,
         'alert_item_content_type_id': self.alert_item_type_id
        }

    def duration(self):
        return self.end - self.begin

    def begin_event(self):
        return None

    def end_event(self):
        return None

    class Meta:
        unique_together = ('alert_item_type', 'alert_item_id', 'alert_type', 'active')
        app_label = 'chroma_core'

    @classmethod
    def subclasses(cls, exclude=[]):
        all_subclasses = []
        for subclass in cls.__subclasses__():
            if subclass.__name__ in exclude:
                continue
            all_subclasses.append(subclass)
            all_subclasses.extend(subclass.subclasses(exclude))
        return all_subclasses

    @classmethod
    def filter_by_item(cls, item):
        if hasattr(item, 'content_type'):
            # A DowncastMetaclass object
            return cls.objects.filter(active = True,
                    alert_item_id = item.id,
                    alert_item_type = item.content_type)
        else:
            return cls.objects.filter(active = True,
                    alert_item_id = item.pk,
                    alert_item_type__model = item.__class__.__name__.lower(),
                    alert_item_type__app_label = item.__class__._meta.app_label)

    @classmethod
    def filter_by_item_id(cls, item_class, item_id):
        return cls.objects.filter(active = True,
                alert_item_id = item_id,
                alert_item_type__model = item_class.__name__.lower(),
                alert_item_type__app_label = item_class._meta.app_label)

    @classmethod
    def filter_by_item_ids(cls, item_class, item_ids):
        return cls.objects.filter(active = True,
                alert_item_id__in = item_ids,
                alert_item_type__model = item_class.__name__.lower(),
                alert_item_type__app_label = item_class._meta.app_label)

    @classmethod
    def notify(cls, alert_item, active, **kwargs):
        return cls._notify(alert_item, active, False, **kwargs)

    @classmethod
    def notify_quiet(cls, alert_item, active, **kwargs):
        return cls._notify(alert_item, active, True, **kwargs)

    @classmethod
    def _notify(cls, alert_item, active, dismissed, **kwargs):
        if hasattr(alert_item, 'content_type'):
            alert_item = alert_item.downcast()

        if active:
            return cls.high(alert_item, dismissed, **kwargs)
        else:
            return cls.low(alert_item, **kwargs)

    @classmethod
    def high(cls, alert_item, dismissed, **kwargs):
        if hasattr(alert_item, 'not_deleted') and alert_item.not_deleted != True:
            return None

        from django.db import IntegrityError
        now = django_now()
        try:
            alert_state = cls.filter_by_item(alert_item).get(**kwargs)
            alert_state.end = now
            alert_state.save()
        except cls.DoesNotExist:
            from chroma_core.lib.job import job_log
            job_log.info("AlertState: Raised %s on %s" % (cls, alert_item))
            if not 'alert_type' in kwargs:
                kwargs['alert_type'] = cls.__name__
            alert_state = cls(
                    active = True,
                    begin = now,
                    end = now,
                    dismissed = dismissed,
                    alert_item = alert_item, **kwargs)
            try:
                alert_state.save()
                be = alert_state.begin_event()
                if be:
                    be.save()
            except IntegrityError, e:
                job_log.warning("AlertState: IntegrityError %s saving %s : %s : %s" % (e, cls.__name__, alert_item, kwargs))
                # Handle colliding inserts: drop out here, no need to update
                # the .end of the existing record as we are logically concurrent
                # with the creator.
                return None
        return alert_state

    @classmethod
    def low(cls, alert_item, **kwargs):
        now = django_now()
        try:
            alert_state = cls.filter_by_item(alert_item).get(**kwargs)
            alert_state.end = now
            alert_state.active = None
            alert_state.save()
            ee = alert_state.end_event()
            if ee:
                ee.save()
        except cls.DoesNotExist:
            alert_state = None

        return alert_state


class AlertSubscription(models.Model):
    """Represents a user's election to be notified of specific alert classes"""
    from django.contrib.auth.models import User

    user = models.ForeignKey(User, related_name='alert_subscriptions')
    alert_type = models.ForeignKey(ContentType)
    # TODO: alert thresholds?

    class Meta:
        app_label = 'chroma_core'


class AlertEmail(models.Model):
    """Record of which alerts an email has been emitted for"""
    alerts = models.ManyToManyField(AlertState)

    class Meta:
        app_label = 'chroma_core'

    def __str__(self):
        str = ""
        for a in self.alerts.all():
            str += " %s" % a
        return str
