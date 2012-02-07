
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import patterns
import chroma_ui.views as views

urlpatterns = patterns('',
    (r'^$', views.index),

    (r'^installation/$', views.installation),
    (r'^installation_status/$', views.installation_status),

    (r'^configure/$', views.configure),
    (r'^configure/filesystems_tab/', views.filesystem_tab),
    (r'^configure/mgts_tab/', views.mgt_tab),
    (r'^configure/volumes_tab/', views.volume_tab),
    (r'^configure/servers_tab/', views.server_tab),
    (r'^configure/storage_tab/', views.storage_tab),
    (r'^configure/filesystems_new/', views.filesystem_create_tab),
    (r'^configure/filesystems_edit/', views.filesystem_edit_tab),

    (r'^dashboard/$', views.dashboard),
    (r'^dashboard/dbalerts/', views.dbalerts),
    (r'^dashboard/dbevents/', views.dbevents),
    (r'^dashboard/dblogs/', views.dblogs),

    (r'^states/$', views.states),
    (r'^set_state/(?P<content_type_id>\d+)/(?P<stateful_object_id>\d+)/(?P<new_state>\w+)/$', views.set_state),
    (r'^jobs_json/$', views.jobs_json),
    (r'^job/(?P<job_id>\d+)/$', views.job),
)
