
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import *
from views import (dashboard,
                   dbalerts,
                   dbevents,
                   dblogs,
                   get_db_logs,
                   get_db_events)

urlpatterns = patterns('',
    (r'^$', dashboard),
    (r'^dbalerts/', dbalerts),
    (r'^dbevents/', dbevents),
    (r'^dblogs/', dblogs),
    # following requests are for JQuery datatables
    (r'^get_dt_logs/', get_db_logs),
    (r'^get_dt_events/', get_db_events),
)
