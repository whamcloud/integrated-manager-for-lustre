# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import logging

from django.db import models
from django.db.models import CASCADE
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.db import IntegrityError

from chroma_core.models.sparse_model import SparseModel
from chroma_core.models.utils import STR_TO_SEVERITY
from chroma_core.lib.job import job_log


class AlertStateBase(SparseModel):
    class Meta:
        unique_together = ("alert_item_type", "alert_item_id", "alert_type", "active")
        ordering = ["id"]
        app_label = "chroma_core"
        db_table = "chroma_core_alertstate"

    table_name = "chroma_core_alertstate"

    """Records a period of time during which a particular
       issue affected a particular element of the system"""
    alert_item_type = models.ForeignKey(ContentType, null=True, on_delete=CASCADE)
    alert_item_id = models.PositiveIntegerField(null=True)
    # FIXME: generic foreign key does not automatically set up deletion
    # of this when the alert_item is deleted -- do it manually
    alert_item = GenericForeignKey("alert_item_type", "alert_item_id")

    alert_type = models.CharField(max_length=128)

    begin = models.DateTimeField(help_text="Time at which the alert started", default=timezone.now)
    end = models.DateTimeField(
        help_text="Time at which the alert was resolved\
            if active is false, else time that the alert was last checked (e.g.\
            time when we last checked an offline target was still not offline)",
        null=True,
    )

    _message = models.TextField(
        db_column="message", null=True, help_text="Message associated with the Alert. Created at Alert creation time"
    )

    # Note: use True and None instead of True and False so that
    # unique-together constraint only applied to active alerts
    active = models.NullBooleanField()

    # whether a user has manually dismissed alert
    dismissed = models.BooleanField(
        default=False, help_text="True denotes that the user " "has acknowledged this alert."
    )

    severity = models.IntegerField(
        default=logging.INFO,
        help_text=("String indicating the " "severity of the alert, " "one of %s") % STR_TO_SEVERITY.keys(),
    )

    # This is only used by one event ClientConnectEvent but it is critical and so needs to be searchable etc
    # for that reason it can't use the variant
    lustre_pid = models.IntegerField(null=True)

    # Subclasses set this, used as a default in .notify()
    default_severity = logging.INFO

    # For historical compatibility anything called Alert will send and alert email and anything else won't.
    # This can obviously be overridden by any particular event but gives us a like for behaviour.
    @property
    def require_mail_alert(self):
        return "Alert'>" in str(type(self))

    def get_active_bool(self):
        return bool(self.active)

    def set_active_bool(self, value):
        if value:
            self.active = True
        else:
            self.active = None

    active_bool = property(get_active_bool, set_active_bool)

    def to_dict(self):
        from chroma_core.lib.util import time_str

        return {
            "alert_severity": "alert",  # FIXME: Still need to figure out weather to pass enum or display string.
            "alert_item": str(self.alert_item),
            "alert_message": self.message(),
            "message": self.message(),
            "active": bool(self.active),
            "begin": time_str(self.begin),
            "end": time_str(self.end) if self.end is not None else time_str(self.begin),
            "id": self.id,
            "alert_item_id": self.alert_item_id,
            "alert_item_content_type_id": self.alert_item_type_id,
        }

    @property
    def affected_objects(self):
        """
        :return: A list of objects other than the alert_item that are affected by this alert
        """
        return []

    def end_event(self):
        return None

    def alert_message(self):
        raise NotImplementedError()

    def message(self):
        # The first time this is call __message will be none, so we have to call alert_message to
        # create the message and then save it. This will occur once for each message.
        # In the future for new alerts we will try and create them when the Alert is created but
        # at the time this patch is produced that is tricky.
        # The purpose of this is to make it so that Alerts can continue to operate when the data required
        # to create the message no longer exists.
        # It's a small step for HYD-5736 and a move towards a more efficient model.
        if self._message is None:
            self._message = self.alert_message()
            self.save()

        return self._message

    def affected_targets(self, affect_target):
        pass

    @classmethod
    def subclasses(cls):
        all_subclasses = []
        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(subclass.subclasses())
        return all_subclasses

    @classmethod
    def filter_by_item(cls, item):
        if hasattr(item, "content_type"):
            # A DowncastMetaclass object
            return cls.objects.filter(active=True, alert_item_id=item.id, alert_item_type=item.content_type)
        else:
            return cls.objects.filter(
                active=True,
                alert_item_id=item.pk,
                alert_item_type__model=item.__class__.__name__.lower(),
                alert_item_type__app_label=item.__class__._meta.app_label,
            )

    @classmethod
    def filter_by_item_id(cls, item_class, item_id):
        return cls.objects.filter(
            active=True,
            alert_item_id=item_id,
            alert_item_type__model=item_class.__name__.lower(),
            alert_item_type__app_label=item_class._meta.app_label,
        )

    @classmethod
    def notify(cls, alert_item, active, **kwargs):
        """Notify an alert in the default severity level for that alert"""

        return cls._notify(alert_item, active, **kwargs)

    @classmethod
    def notify_warning(cls, alert_item, active, **kwargs):
        """Notify an alert in at most the WARNING severity level"""

        kwargs["attrs_to_save"] = {"severity": min(cls.default_severity, logging.WARNING)}
        return cls._notify(alert_item, active, **kwargs)

    @classmethod
    def _notify(cls, alert_item, active, **kwargs):
        if hasattr(alert_item, "content_type"):
            alert_item = alert_item.downcast()

        if active:
            return cls.high(alert_item, **kwargs)
        else:
            return cls.low(alert_item, **kwargs)

    @classmethod
    def _get_attrs_to_save(cls, kwargs):
        # Prepare data to be saved with alert, but not effect the filter_by_item() below
        # e.g. Only one alert type per alert item can be active, so we don't need to filter on severity.
        attrs_to_save = kwargs.pop("attrs_to_save", {})

        # Add any properties to the attrs_to_save that are not db fields, we can't search on
        # non db fields after all. Some alerts have custom fields and they will be searched out here.
        fields = [field.attname for field in cls._meta.fields]
        for attr in kwargs.keys():
            if attr not in fields:
                attrs_to_save[attr] = kwargs.pop(attr)

        return attrs_to_save

    @classmethod
    def high(cls, alert_item, **kwargs):
        if hasattr(alert_item, "not_deleted") and alert_item.not_deleted != True:
            return None

        attrs_to_save = cls._get_attrs_to_save(kwargs)

        try:
            alert_state = cls.filter_by_item(alert_item).get(**kwargs)
        except cls.DoesNotExist:
            kwargs.update(attrs_to_save)

            if not "alert_type" in kwargs:
                kwargs["alert_type"] = cls.__name__
            if not "severity" in kwargs:
                kwargs["severity"] = cls.default_severity

            alert_state = cls(
                active=True, dismissed=False, alert_item=alert_item, **kwargs  # Users dismiss, not the software
            )
            try:
                alert_state._message = alert_state.alert_message()
                alert_state.save()
                job_log.info(
                    "AlertState: Raised %s on %s "
                    "at severity %s" % (cls, alert_state.alert_item, alert_state.severity)
                )
            except IntegrityError as e:
                job_log.warning(
                    "AlertState: IntegrityError %s saving %s : %s : %s" % (e, cls.__name__, alert_item, kwargs)
                )
                # Handle colliding inserts: drop out here, no need to update
                # the .end of the existing record as we are logically concurrent
                # with the creator.
                return None
        return alert_state

    @classmethod
    def low(cls, alert_item, **kwargs):
        # The caller may provide an end_time rather than wanting now()
        end_time = kwargs.pop("end_time", timezone.now())

        # currently, no attrs are saved when an attr is lowered, so just filter them out of kwargs
        cls._get_attrs_to_save(kwargs)

        try:
            alert_state = cls.filter_by_item(alert_item).get(**kwargs)
            alert_state.end = end_time
            alert_state.active = None
            alert_state.save()

            # We optionally emit an event when alerts are lowered: we don't do that
            # for the beginning because that is implicit in the alert itself, whereas
            # the end can reasonably have a different message.
            end_event = alert_state.end_event()
            if end_event:
                end_event.register_event(
                    end_event.alert_item,
                    severity=end_event.severity,
                    message_str=end_event.message_str,
                    alert=end_event.alert,
                )
        except cls.DoesNotExist:
            alert_state = None

        return alert_state

    @classmethod
    def register_event(cls, alert_item, **kwargs):
        # Events are Alerts with no duration, so just go high/low.
        alert_state = cls.high(alert_item, attrs_to_save=kwargs)
        cls.low(alert_item, end_time=alert_state.begin, attrs_to_save=kwargs)

    def cast(self, target_class):
        """
        Works exactly as the super except because we duplicate record_type with alert_type. We should remove in the
        future, but for now this fixes that up.
        :param target_class:
        :return:
        """
        # If the save fails for some reason then this change will have no affect.
        self.alert_type = target_class._meta.object_name

        new_alert = super(AlertStateBase, self).cast(target_class)

        # The message may well have changed so regenerate it.
        new_alert._message = None
        new_alert.message()

        return new_alert


class AlertState(AlertStateBase):
    # This is worse than INFO because it *could* indicate that
    # a filesystem is unavailable, but it is not necessarily
    # so:
    # * Host can lose contact with us but still be servicing clients
    # * Host can be offline entirely but filesystem remains available
    #   if failover servers are available.
    default_severity = logging.WARNING

    is_sparse_base = True

    class Meta:
        app_label = "chroma_core"
        proxy = True


class AlertSubscription(models.Model):
    """Represents a user's election to be notified of specific alert classes"""

    user = models.ForeignKey(User, related_name="alert_subscriptions", on_delete=CASCADE)
    alert_type = models.ForeignKey(ContentType, on_delete=CASCADE)
    # TODO: alert thresholds?

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @property
    def alert_type_name(self):
        """
        Pre 3.0 we stored the needed the ContentType but now we need the alert_type as a string
        :return: Alert type as a string
        """
        name = self.alert_type.name

        # Turn bobs big alert into BobsBigAlert
        return "".join(["%s%s" % (element[0].upper(), element[1:].lower()) for element in name.split(" ")])


class AlertEmail(models.Model):
    """Record of which alerts an email has been emitted for"""

    alerts = models.ManyToManyField(AlertState)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    def __str__(self):
        str = ""
        for a in self.alerts.all():
            str += " %s" % a
        return str
