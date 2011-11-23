
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import patterns
import views

urlpatterns = patterns('',
    (r'^$', views.hydracm),
    (r'^config/.*$', views.hydracm),
    (r'^filesystems_tab/', views.hydracmfstab),
    (r'^mgts_tab/', views.hydracmmgttab),
    (r'^volumes_tab/', views.hydracmvolumetab),
    (r'^servers_tab/', views.hydracmservertab),
    (r'^storage_tab/', views.storage_tab),
    (r'^filesystems_new/', views.hydracmnewfstab),
    (r'^filesystems_edit/', views.hydracmeditfs),

    (r'^states/$', views.states),
    (r'^set_state/(?P<content_type_id>\d+)/(?P<stateful_object_id>\d+)/(?P<new_state>\w+)/$', views.set_state),
    (r'^jobs_json/$', views.jobs_json),
    (r'^job/(?P<job_id>\d+)/$', views.job),
)
