#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import datetime
import dateutil.tz
from django.db import models
from chroma_core.models.server_profile import ServerProfile
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

    profile = models.ForeignKey(ServerProfile, null=True)
    # FIXME: need to change back the default when migration has been done
    #profile = models.ForeignKey(ServerProfile, default=lambda: ServerProfile.objects.get(name='default'))

    def save(self, *args, **kwargs):
        assert self.profile
        super(RegistrationToken, self).save(*args, **kwargs)

    class Meta:
        app_label = 'chroma_core'
