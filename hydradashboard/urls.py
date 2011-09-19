
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import *
from views import dashboard
urlpatterns = patterns('',
    (r'^$', dashboard),
)
