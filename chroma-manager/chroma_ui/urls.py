
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import patterns
import chroma_ui.views as views

urlpatterns = patterns('',
    (r'^.*', views.index),
)
