#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.conf.urls.defaults import patterns, include

from django.contrib import admin

admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

import chroma_ui.urls
import chroma_api.urls
import chroma_agent_comms.urls

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^agent/', include(chroma_agent_comms.urls)),
    (r'^ui/', include(chroma_ui.urls)),
    (r'^', include(chroma_api.urls)),
)

urlpatterns += staticfiles_urlpatterns()
