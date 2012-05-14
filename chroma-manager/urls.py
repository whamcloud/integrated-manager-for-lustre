#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.conf.urls.defaults import patterns, include

from django.contrib import admin
admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns


# HYD-646: Patch tastypie to assume timezone-naive datetimes are in UTC
# to match our DB convention (see WorkaroundDateTimeField)
from dateutil import tz
import datetime

import tastypie.fields


class ZuluDateTimeField(tastypie.fields.DateTimeField):
    def convert(self, value):
        if isinstance(value, datetime.datetime):
            if value.tzinfo == None:
                value = value.replace(tzinfo = tz.tzutc())

        return value

tastypie.fields.DateTimeField = ZuluDateTimeField

import chroma_ui.urls
import chroma_api.urls

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),

    (r'^ui/', include(chroma_ui.urls)),

    (r'^', include(chroma_api.urls)),
)

urlpatterns += staticfiles_urlpatterns()
