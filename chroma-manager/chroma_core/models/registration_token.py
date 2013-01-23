#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
import dateutil.tz
from django.db import models
import os


SECRET_LENGTH = 16  # Number of bytes in secret, double to get number of alphanumeric characters
DEFAULT_EXPIRY_SECONDS = 60
DEFAULT_CREDITS = 1


def _tzaware_future_offset(offset):
    now = datetime.datetime.now(dateutil.tz.tzutc())
    return now + datetime.timedelta(seconds = offset)


class RegistrationToken(models.Model):
    """
    Authorization tokens handed out to servers to grant them
    the right to register themselves with the manager.
    """
    expiry = models.DateTimeField(
        default = lambda: _tzaware_future_offset(DEFAULT_EXPIRY_SECONDS),
        help_text = "DateTime, at which time this token will expire.  Defaults to %s seconds in the future." % DEFAULT_EXPIRY_SECONDS
    )
    cancelled = models.BooleanField(
        default = False,
        help_text = "Boolean, whether this token has been manually cancelled.  Once this is set, the" +
                    "token will no longer be accessible.  Initially false.")
    secret = models.CharField(
        max_length = SECRET_LENGTH * 2,
        default = lambda: "".join(["%.2X" % ord(b) for b in os.urandom(SECRET_LENGTH)]),
        help_text = "String, the secret used by servers to authenticate themselves (%d characters alphanumeric)" % SECRET_LENGTH * 2)
    credits = models.IntegerField(
        default = DEFAULT_CREDITS,
        help_text = "Integer, the number of servers which may register using this token before it expires (default %s)" % DEFAULT_CREDITS)

    class Meta:
        app_label = 'chroma_core'
