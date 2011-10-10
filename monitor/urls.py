
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import *

from monitor.views import *

urlpatterns = patterns('',
    (r'^$', dashboard),
    (r'^dashboard_inner/$', dashboard_inner),
    (r'^host/$', host),
    (r'^log_viewer/$', log_viewer),
    (r'^events/$', events),
    (r'^alerts/$', alerts),
)
