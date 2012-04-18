#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.conf.urls.defaults import patterns
import chroma_ui.views as views

urlpatterns = patterns('',
    (r'^.*', views.index),
)
