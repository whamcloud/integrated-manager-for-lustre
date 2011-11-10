
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models, transaction
from polymorphic.models import DowncastMetaclass
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from collections import defaultdict

import simplejson as json
import pickle

from logging import INFO, WARNING

class WorkaroundGenericForeignKey(GenericForeignKey):
    """TEMPORARY workaround for django bug #16048 while we wait for
       a fixed django to get released"""
    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        try:
            return getattr(instance, self.cache_attr)
        except AttributeError:
            rel_obj = None

            # Make sure to use ContentType.objects.get_for_id() to ensure that
            # lookups are cached (see ticket #5570). This takes more code than
            # the naive ``getattr(instance, self.ct_field)``, but has better
            # performance when dealing with GFKs in loops and such.
            f = self.model._meta.get_field(self.ct_field)
            ct_id = getattr(instance, f.get_attname(), None)
            if ct_id:
                ct = self.get_content_type(id=ct_id, using=instance._state.db)
                from django.core.exceptions import ObjectDoesNotExist
                try:
                    rel_obj = ct.model_class()._base_manager.using(ct._state.db).get(pk=getattr(instance, self.fk_field))

                except ObjectDoesNotExist:
                    pass
            setattr(instance, self.cache_attr, rel_obj)
            return rel_obj

from polymorphic.models import DowncastManager
class DeletableManager(DowncastManager):
    """Filters results to return only not-deleted records"""
    def get_query_set(self):
        return super(DeletableManager, self).get_query_set().filter(not_deleted = True)

from polymorphic.models import PolymorphicMetaclass
class DeletableDowncastableMetaclass(PolymorphicMetaclass):
    """Make a django model 'downcastable and 'deletable'.

    This combines the DowncastMetaclass behavior with the not_deleted attribute,
    the delete() method and the DeletableManager.

    The not_deleted attribute is logically a True/False 'deleted' attribute, but is
    implemented this (admittedly ugly) way in order to work with django's 
    unique_together option.  When 'not_deleted' is included in the unique_together
    tuple, the uniqeness constraint is applied only to objects which have not
    been deleted -- e.g. an MGS can only have one filesystem with a given name, but
    once you've deleted that filesystem you should be able to create more with the 
    same name.

    The manager we set is a subclass of polymorphic.models.DowncastManager, so we inherit the
    full DowncastMetaclass behaviour.
    """
    def __new__(cls, name, bases, dct):
        @classmethod
        # commit_on_success to ensure that the object is only marked deleted
        # if the updates to alerts also succeed
        @transaction.commit_on_success
        def delete(clss, id):
            """Mark a record as deleted, returns nothing.
            
            Looks up the model instance by pk, sets the not_deleted attribute
            to None and saves the model instance.

            Additionally marks any AlertStates referring to this item as inactive.

            This is provided as a class method which takes an ID rather than as an
            instance method, in order to use ._base_manager rather than .objects -- this
            allows us to find the object even if it was already deleted, making this
            operation idempotent rather than throwing a DoesNotExist on the second try.
            """
            # Not implemented as an instance method because
            # we will need to use _base_manager to ensure
            # we can get at the object
            instance = clss._base_manager.get(pk = id).downcast()
            klass = instance.content_type.model_class()

            if instance.not_deleted:
                instance.not_deleted = None
                instance.save()

            from monitor.lib.lustre_audit import audit_log
            updated = AlertState.filter_by_item_id(klass, id).update(active = False)
            audit_log.info("Lowered %d alerts while deleting %s %s" % (updated, klass, id))

        dct['objects'] = DeletableManager()
        dct['delete']  = delete
        # Conditional to only create the 'deleted' attribute on the immediate 
        # user of the metaclass, not again on subclasses.
        if issubclass(dct.get('__metaclass__', type), DeletableDowncastableMetaclass):
            # Please forgive me.  Logically this would be a field called 'deleted' which would
            # be True or False.  Instead, it is a field called 'not_deleted' which can be
            # True or None.  The reason is: unique_together constraints.
            dct['not_deleted'] = models.NullBooleanField(default = True)

        if dct.has_key('Meta'):
            if hasattr(dct['Meta'], 'unique_together'):
                if not 'not_deleted' in dct['Meta'].unique_together:
                    dct['Meta'].unique_together = dct['Meta'].unique_together + ('not_deleted',)

        return super(DeletableDowncastableMetaclass, cls).__new__(cls, name, bases, dct)

class MeasuredEntity(object):
    """Provides mix-in access to metrics specific to the instance."""
    def __get_metrics(self):
        from metrics import get_instance_metrics
        self._metrics = get_instance_metrics(self)
        return self._metrics

    metrics = property(__get_metrics)

#class Router(models.Model, MeasuredEntity):
#    host = models.ForeignKey(Host)



#class Client(Mountable, FilesystemMember):
#    def role(self):
#        return "Client"
#
#    def status_string(self):
#        # Look for alerts that can affect this item:
#        # statuses are STARTED STOPPED
#        alerts = AlertState.filter_by_item(self)
#        alert_klasses = [a.__class__ for a in alerts]
#        if len(alerts) == 0:
#            return "STARTED"
#        if MountableOfflineAlert in alert_klasses:
#            return "STOPPED"
#        raise NotImplementedError("Unhandled target alert %s" % alert_klasses)
#
#    def __str__(self):
#        return "%s-client %d" % (self.filesystem.name, self.id)

class Event(models.Model):
    __metaclass__ = DowncastMetaclass

    created_at = models.DateTimeField(auto_now_add = True)
    severity = models.IntegerField()
    host = models.ForeignKey('configure.ManagedHost', blank = True, null = True)

    @staticmethod
    def type_name():
        raise NotImplementedError

    def severity_class(self):
        # CSS class from an Event severity -- FIXME: this should be a templatetag
        from logging import INFO, WARNING, ERROR
        try:
            return {INFO: 'info', WARNING: 'warning', ERROR: 'error'}[self.severity]
        except KeyError:
            return ""

    def message(self):
        raise NotImplementedError

class LearnEvent(Event):
    # Every environment at some point reinvents void* :-)
    learned_item_type = models.ForeignKey(ContentType)
    learned_item_id = models.PositiveIntegerField()
    learned_item = WorkaroundGenericForeignKey('learned_item_type', 'learned_item_id')

    @staticmethod
    def type_name():
        return "Autodetection"

    def message(self):
        from configure.models import ManagedTargetMount, ManagedTarget, ManagedFilesystem
        if isinstance(self.learned_item, ManagedTargetMount):
            return "Discovered mount point of %s on %s" % (self.learned_item, self.learned_item.host)
        elif isinstance(self.learned_item, ManagedTarget):
            return "Discovered formatted target %s" % (self.learned_item)
        elif isinstance(self.learned_item, ManagedFilesystem):
            return "Discovered filesystem %s on MGS %s" % (self.learned_item, self.learned_item.mgs.primary_server())
        else:
            return "Discovered %s" % self.learned_item

class AlertEvent(Event):
    message_str = models.CharField(max_length = 512)
    alert = models.ForeignKey('AlertState')

    @staticmethod
    def type_name():
        return "Alert"

    def message(self):
        return self.message_str

class SyslogEvent(Event):
    message_str = models.CharField(max_length = 512)
    lustre_pid = models.IntegerField(null = True)

    @staticmethod
    def type_name():
        return "Syslog"

    def message(self):
        return self.message_str

class ClientConnectEvent(SyslogEvent):

    @staticmethod
    def type_name():
        return "ClientConnect"

class AlertState(models.Model):
    """Records a period of time during which a particular
       issue affected a particular element of the system"""
    __metaclass__ = DowncastMetaclass

    alert_item_type = models.ForeignKey(ContentType, related_name='alertstate_alert_item_type')
    alert_item_id = models.PositiveIntegerField()
    # FIXME: generic foreign key does not automatically set up deletion
    # of this when the alert_item is deleted -- do it manually
    alert_item = WorkaroundGenericForeignKey('alert_item_type', 'alert_item_id')

    begin = models.DateTimeField()
    end = models.DateTimeField()

    # Note: use True and None instead of True and False so that
    # unique-together constraint only applied to active alerts
    active = models.NullBooleanField()

    def to_dict(self):
        from monitor.lib.util import time_str
        return {
         # FIXME: retire misnamed 'alert_created_at'
         'alert_created_at': self.begin,
         'alert_created_at_short': self.begin,
         'begin': self.begin,
         'end': self.end,
         'alert_severity':'alert', # FIXME: Still need to figure out wheather to pass enum or display string.
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
        unique_together = ('alert_item_type', 'alert_item_id', 'content_type', 'active')

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
    def notify(alert_klass, alert_item, active, **kwargs):
        if hasattr(alert_item, 'content_type'):
            alert_item = alert_item.downcast()

        if active:
            return alert_klass.high(alert_item, **kwargs)
        else:
            return alert_klass.low(alert_item, **kwargs)

    @classmethod
    def high(alert_klass, alert_item, **kwargs):
        import datetime
        from django.db import IntegrityError
        now = datetime.datetime.now()
        try:
            alert_state = alert_klass.filter_by_item(alert_item).get(**kwargs)
            created = False
        except alert_klass.DoesNotExist:
            alert_state = alert_klass(
                    active = True,
                    begin = now,
                    end = now,
                    alert_item = alert_item, **kwargs)
            try:
                alert_state.save()
                created = True
            except IntegrityError:
                # Handle colliding inserts
                # NB not using get_or_create because of GenericForeignKey (https://code.djangoproject.com/ticket/2316)
                alert_state = alert_klass.filter_by_item(alert_item).get(**kwargs)
                created = False

        if created:
            be = alert_state.begin_event()
            if be:
                be.save()
        else:
            alert_state.end = now
            alert_state.save()

        return alert_state

    @classmethod
    def low(alert_klass, alert_item, **kwargs):
        import datetime
        now = datetime.datetime.now()
        try:
            alert_state = alert_klass.filter_by_item(alert_item).get(**kwargs)
            alert_state.end = now
            alert_state.active = None
            alert_state.save()
            ee = alert_state.end_event()
            if ee:
                ee.save()
        except alert_klass.DoesNotExist:
            alert_state = None

        return alert_state

class TargetOfflineAlert(AlertState):
    def message(self):
        return "Target %s offline" % (self.alert_item)

    def begin_event(self):
        return AlertEvent(
                message_str = "%s stopped" % self.alert_item,
                host = self.alert_item.primary_server(),
                alert = self,
                severity = WARNING)
        
    def end_event(self):
        return AlertEvent(
                message_str = "%s started" % self.alert_item,
                host = self.alert_item.primary_server(),
                alert = self,
                severity = INFO)

class TargetFailoverAlert(AlertState):
    def message(self):
        return "Target %s failed over to server %s" % (self.alert_item.target, self.alert_item.host)

    def begin_event(self):
        # FIXME: reporting this event against the primary server
        # of a target because we don't have enough information 
        # to 
        return AlertEvent(
                message_str = "%s failover mounted" % self.alert_item.target,
                host = self.alert_item.host,
                alert = self,
                severity = WARNING)
        
    def end_event(self):
        return AlertEvent(
                message_str = "%s failover unmounted" % self.alert_item.target,
                host = self.alert_item.host,
                alert = self,
                severity = INFO)

class TargetRecoveryAlert(AlertState):
    def message(self):
        return "Target %s in recovery" % self.alert_item

    def begin_event(self):
        return AlertEvent(
                message_str = "Target '%s' went into recovery" % self.alert_item,
                host = self.alert_item.primary_server(),
                alert = self,
                severity = WARNING)

    def end_event(self):
        return AlertEvent(
                message_str = "Target '%s' completed recovery" % self.alert_item,
                host = self.alert_item.primary_server(),
                alert = self,
                severity = INFO)

class HostContactAlert(AlertState):
    def message(self):
        return "Lost contact with host %s" % self.alert_item

    def begin_event(self):
        return AlertEvent(
                message_str = "Lost contact with host %s" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = WARNING)

    def end_event(self):
        return AlertEvent(
                message_str = "Re-established contact with host %s" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = INFO)

class LNetOfflineAlert(AlertState):
    def message(self):
        return "LNet offline on server %s" % self.alert_item

    def begin_event(self):
        return AlertEvent(
                message_str = "LNet stopped on host '%s'" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = WARNING)

    def end_event(self):
        return AlertEvent(
                message_str = "LNet started on host '%s'" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = INFO)

class TargetParam(models.Model):
    target = models.ForeignKey('configure.ManagedTarget')
    key = models.CharField(max_length=128)
    value = models.CharField(max_length=512)

    @staticmethod
    def update_params(target, params):
        from monitor.lib.lustre_audit import audit_log

        old_params = set(target.get_params())

        new_params = set()
        for key, value_list in params.items():
            for value in value_list:
                new_params.add((key, value))
        
        for del_param in old_params - new_params:
            target.targetparam_set.get(key = del_param[0], value = del_param[1]).delete()
            audit_log.info("del_param: %s" % (del_param,))
        for add_param in new_params - old_params:
            target.targetparam_set.create(key = add_param[0], value = add_param[1])
            audit_log.info("add_param: %s" % (add_param,))

class TargetRecoveryInfo(models.Model):
    # When a volume is present, we will have been able to interrogate 
    # its recovery status
    # JSON-encoded dict parsed from /proc/fs/lustre/*/*/recovery_status
    recovery_status = models.TextField()

    target = models.ForeignKey('configure.ManagedTarget')

    from django.db import transaction
    @staticmethod
    @transaction.commit_on_success
    def update(target, recovery_status):
        TargetRecoveryInfo.objects.filter(target = target).delete()
        instance = TargetRecoveryInfo.objects.create(
                target = target,
                recovery_status = json.dumps(recovery_status))
        return instance.is_recovering(recovery_status) 

    def is_recovering(self, data = None):
        if not data:
            data = json.loads(self.recovery_status)
        return (data.has_key("status") and data["status"] == "RECOVERING")

    def recovery_status_str(self):
        data = json.loads(self.recovery_status)
        if data.has_key("status") and data["status"] == "RECOVERING":
            return "%s %ss remaining" % (data["status"], data["time_remaining"])
        elif data.has_key("status"):
            return data["status"]
        else:
            return "N/A"

class Systemevents(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    customerid = models.BigIntegerField(null=True, db_column='CustomerID',
                                        blank=True)
    receivedat = models.DateTimeField(null=True, db_column='ReceivedAt',
                                      blank=True)
    devicereportedtime = models.DateTimeField(null=True,
                                              db_column='DeviceReportedTime',
                                              blank=True)
    facility = models.IntegerField(null=True, db_column='Facility',
                                   blank=True)
    priority = models.IntegerField(null=True, db_column='Priority',
                                   blank=True)
    fromhost = models.CharField(max_length=60, db_column='FromHost',
                                blank=True)
    message = models.TextField(db_column='Message', blank=True)
    ntseverity = models.IntegerField(null=True, db_column='NTSeverity',
                                     blank=True)
    importance = models.IntegerField(null=True, db_column='Importance',
                                     blank=True)
    eventsource = models.CharField(max_length=60, db_column='EventSource',
                                   blank=True)
    eventuser = models.CharField(max_length=60, db_column='EventUser',
                                 blank=True)
    eventcategory = models.IntegerField(null=True, db_column='EventCategory',
                                        blank=True)
    eventid = models.IntegerField(null=True, db_column='EventID', blank=True)
    eventbinarydata = models.TextField(db_column='EventBinaryData',
                                       blank=True)
    maxavailable = models.IntegerField(null=True, db_column='MaxAvailable',
                                       blank=True)
    currusage = models.IntegerField(null=True, db_column='CurrUsage',
                                    blank=True)
    minusage = models.IntegerField(null=True, db_column='MinUsage', blank=True)
    maxusage = models.IntegerField(null=True, db_column='MaxUsage', blank=True)
    infounitid = models.IntegerField(null=True, db_column='InfoUnitID',
                                     blank=True)
    syslogtag = models.CharField(max_length=60, db_column='SysLogTag',
                                 blank=True)
    eventlogtype = models.CharField(max_length=60, db_column='EventLogType',
                                    blank=True)
    genericfilename = models.CharField(max_length=60,
                                       db_column='GenericFileName', blank=True)
    systemid = models.IntegerField(null=True, db_column='SystemID',
                                   blank=True)
    class Meta:
        db_table = u'SystemEvents'

    def get_message_class(self):
        if self.message.startswith(" LustreError:"):
            return "lustre_error"
        elif self.message.startswith(" Lustre:"):
            return "lustre"
        else:
            return "normal"

class LastSystemeventsProcessed(models.Model):
    last = models.IntegerField(default = 0)

class FrontLineMetricStore(models.Model):
    """Fast simple metrics store.  Should be backed by MEMORY engine."""
    content_type    = models.ForeignKey(ContentType, null=True)
    object_id       = models.PositiveIntegerField(null=True)
    content_object  = GenericForeignKey('content_type', 'object_id')
    insert_time     = models.DateTimeField()
    metric_name     = models.CharField(max_length=255)
    metric_type     = models.CharField(max_length=64)
    value           = models.FloatField()
    complete        = models.BooleanField(default=False, db_index=True)

    @classmethod
    def store_update(cls, ct, o_id, update_time, update):
        from datetime import datetime as dt
        from django.db import connection, transaction
        cursor = connection.cursor()

        names = update.keys()
        for name in names:
            data = update[name]
            params = [dt.now(), ct.id, o_id, name]
            try:
                params.append(data['type'])
                params.append(data['value'])
            except TypeError:
                # FIXME: do we really want to default this, or raise?
                params.append('Counter')
                params.append(data)

            # Use this to signal that all of the metrics for this update
            # have been inserted.
            params.append(1 if name == names[-1] else 0)

            # Bypass the ORM for this -- we don't care about instantiating
            # objects from these inserts.
            sql = "INSERT into monitor_frontlinemetricstore (insert_time, content_type_id, object_id, metric_name, metric_type, value, complete) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, params)
            transaction.commit_unless_managed()
