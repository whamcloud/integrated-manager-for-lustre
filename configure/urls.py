
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import *

from configure.views import *

urlpatterns = patterns('',
    (r'^$', states),
    (r'^create_mgs/(?P<host_id>\d+)/$', create_mgs),
    (r'^create_filesystem/(?P<mgs_id>\d+)/$', create_fs),
    (r'^create_mds/(?P<host_id>\d+)/$', create_mds),
    (r'^create_oss/(?P<host_id>\d+)/$', create_oss),
    (r'^jobs/$', jobs),
    (r'^jobs_json/$', jobs_json),
    (r'^job/(?P<job_id>\d+)/$', job),
    (r'^job_cancel/(?P<job_id>\d+)/$', job_cancel),
    (r'^job_pause/(?P<job_id>\d+)/$', job_pause),
    (r'^job_unpause/(?P<job_id>\d+)/$', job_unpause),
    (r'^states/$', states),
    (r'^set_state/(?P<content_type_id>\d+)/(?P<stateful_object_id>\d+)/(?P<new_state>\w+)/$', set_state),
    (r'^filesystem/(?P<filesystem_id>\d+)/$', filesystem),
)
