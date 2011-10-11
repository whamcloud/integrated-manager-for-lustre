
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
    (r'^target/(?P<target_id>\d+)/$', target),
    (r'^conf_param_help/(?P<conf_param_name>[\w\._-]+)/$', conf_param_help),
    (r'^storage_resource/(?P<vrr_id>\d+)/$', storage_resource),
    (r'^storage_resource_set_alias/(?P<record_id>\d+)/$', storage_resource_set_alias),
    (r'^storage_browser/$', storage_browser),
    (r'^storage_table/$', storage_table),
    (r'^storage_table_json/(?P<plugin_module>[\w\._-]+)/(?P<resource_class_name>[\w\._-]+)/$', storage_table_json),
)
