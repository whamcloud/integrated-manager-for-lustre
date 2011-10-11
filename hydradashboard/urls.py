
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import *
from views import (dashboard,
                   dbalerts,
                   dbevents,
                   dblogs)  
                  
urlpatterns = patterns('',
    (r'^$', dashboard),
    (r'^dbalerts/', dbalerts),
    (r'^dbevents/', dbevents),
    (r'^dblogs/', dblogs),
)
