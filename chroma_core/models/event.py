
from django.db import models
from polymorphic.models import DowncastMetaclass
from django.contrib.contenttypes.models import ContentType

from chroma_core.models.utils import WorkaroundGenericForeignKey


class Event(models.Model):
    __metaclass__ = DowncastMetaclass

    created_at = models.DateTimeField(auto_now_add = True)
    severity = models.IntegerField()
    host = models.ForeignKey('chroma_core.ManagedHost', blank = True, null = True)

    class Meta:
        app_label = 'chroma_core'

    @staticmethod
    def type_name():
        raise NotImplementedError

    def severity_class(self):
        # CSS class from an Event severity -- FIXME: this should be a templatetag
        try:
            from logging import INFO, WARNING, ERROR
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

    class Meta:
        app_label = 'chroma_core'

    @staticmethod
    def type_name():
        return "Autodetection"

    def message(self):
        from chroma_core.models import ManagedTargetMount, ManagedTarget, ManagedFilesystem
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

    class Meta:
        app_label = 'chroma_core'

    @staticmethod
    def type_name():
        return "Alert"

    def message(self):
        return self.message_str


class SyslogEvent(Event):
    message_str = models.CharField(max_length = 512)
    lustre_pid = models.IntegerField(null = True)

    class Meta:
        app_label = 'chroma_core'

    @staticmethod
    def type_name():
        return "Syslog"

    def message(self):
        return self.message_str


class ClientConnectEvent(SyslogEvent):
    class Meta:
        app_label = 'chroma_core'

    @staticmethod
    def type_name():
        return "ClientConnect"
