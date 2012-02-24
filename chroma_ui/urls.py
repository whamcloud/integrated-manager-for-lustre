
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import patterns
import chroma_ui.views as views

urlpatterns = patterns('',
    (r'^$', views.index),

    #(r'^states/$', views.states),
    #(r'^set_state/(?P<content_type_id>\d+)/(?P<stateful_object_id>\d+)/(?P<new_state>\w+)/$', views.set_state),
    #(r'^jobs_json/$', views.jobs_json),
    (r'^oldjob/(?P<job_id>\d+)/$', views.job),

    (r'^.*', views.index),
)
