# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import models


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
