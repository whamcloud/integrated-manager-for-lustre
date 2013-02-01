#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db import models


class MessageClass:
    NORMAL = 0
    LUSTRE = 1
    LUSTRE_ERROR = 2

    @classmethod
    def to_string(cls, n):
        """Convert a MessageClass ID to a string"""
        if not hasattr(cls, '_to_string'):
            cls._to_string = dict([(v, k) for k, v in cls.__dict__.items() if not k.startswith('_') and isinstance(v, int)])
        return cls._to_string[n]

    @classmethod
    def from_string(cls, s):
        """Convert a string to a MessageClass ID"""
        if not hasattr(cls, '_from_string'):
            cls._from_string = dict([(k, v) for k, v in cls.__dict__.items() if not k.startswith('_') and isinstance(v, int)])
        return cls._from_string[s]


class LogMessage(models.Model):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    datetime = models.DateTimeField()
    # Note: storing FQDN rather than ManagedHost ID because:
    #  * The log store is a likely candidate for moving to a separate data store where
    #    the relational ID of a host is a less sound ID than its name
    #  * It is efficient to avoid looking up fqdn to host ID on insert (log messages
    #    are inserted much more than they are queried).
    fqdn = models.CharField(max_length = 255)
    severity = models.SmallIntegerField()
    facility = models.SmallIntegerField()
    tag = models.CharField(max_length = 63)
    message = models.TextField()
    message_class = models.SmallIntegerField()

    def save(self, *args, **kwargs):
        if self.message_class is None:
            if self.message.startswith("LustreError:"):
                self.message_class = MessageClass.LUSTRE_ERROR
            elif self.message.startswith("Lustre:"):
                self.message_class = MessageClass.LUSTRE
            else:
                self.message_class = MessageClass.NORMAL

        super(LogMessage, self).save(*args, **kwargs)

    def __str__(self):
        return "%s %s %s %s %s" % (self.datetime, self.fqdn, self.priority, self.source, self.message)
