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


from django.db import models
from django.utils.text import Truncator

import httpagentparser


class ClientError(models.Model):
    class Meta:
        app_label = 'chroma_core'

    browser = models.CharField(max_length=255, blank=True)
    os = models.CharField(max_length=255, blank=True)
    cause = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=255)
    stack = models.TextField(blank=True)
    url = models.URLField(verify_exists=False)
    user_agent = models.CharField(max_length=255)

    def __unicode__(self):
        truncator = Truncator(self.message)
        return u'%s: %s' % (self.id, truncator.chars(20))

    def save(self, *args, **kwargs):
        if not self.id:
            self.os, self.browser = httpagentparser.simple_detect(self.user_agent)
        return super(ClientError, self).save(*args, **kwargs)
