# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models

import re


class MessageClass:
    NORMAL = 0
    LUSTRE = 1
    LUSTRE_ERROR = 2

    @classmethod
    def strings(cls):
        return [cls.to_string(i) for i in [cls.NORMAL, cls.LUSTRE, cls.LUSTRE_ERROR]]

    @classmethod
    def to_string(cls, n):
        """Convert a MessageClass ID to a string"""
        if not hasattr(cls, "_to_string"):
            cls._to_string = dict(
                [(v, k) for k, v in cls.__dict__.items() if not k.startswith("_") and isinstance(v, int)]
            )
        return cls._to_string[n]

    @classmethod
    def from_string(cls, s):
        """Convert a string to a MessageClass ID"""
        if not hasattr(cls, "_from_string"):
            cls._from_string = dict(
                [(k, v) for k, v in cls.__dict__.items() if not k.startswith("_") and isinstance(v, int)]
            )
        return cls._from_string[s]


class LogMessage(models.Model):
    class Meta:
        app_label = "chroma_core"
        ordering = ["-datetime"]

    datetime = models.DateTimeField()
    # Note: storing FQDN rather than ManagedHost ID because:
    #  * The log store is a likely candidate for moving to a separate data store where
    #    the relational ID of a host is a less sound ID than its name
    #  * It is efficient to avoid looking up fqdn to host ID on insert (log messages
    #    are inserted much more than they are queried).
    fqdn = models.CharField(
        max_length=255,
        help_text="FQDN of the host from which the message was received.  Note that this host may"
        "no longer exist or its FQDN may have changed since.",
    )
    severity = models.SmallIntegerField(
        help_text="Integer data. `RFC5424 severity <http://tools.ietf.org/html/rfc5424#section-6.2.1>`_"
    )
    facility = models.SmallIntegerField(
        help_text="Integer data. `RFC5424 facility <http://tools.ietf.org/html/rfc5424#section-6.2.1>`_"
    )
    tag = models.CharField(max_length=63)
    message = models.TextField()
    message_class = models.SmallIntegerField()

    @classmethod
    def get_message_class(cls, message):
        log_match = "(\[[\d\.]*\])? ?%s:"

        if re.match(log_match % "LustreError", message):
            return MessageClass.LUSTRE_ERROR
        elif re.match(log_match % "Lustre", message):
            return MessageClass.LUSTRE
        else:
            return MessageClass.NORMAL

    def __str__(self):
        return "%s %s %s %s %s %s" % (self.datetime, self.fqdn, self.severity, self.facility, self.tag, self.message)
