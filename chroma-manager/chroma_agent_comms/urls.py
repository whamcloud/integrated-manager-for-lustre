#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.conf.urls import patterns
import chroma_agent_comms.views as views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = patterns('',
    (r'^message/$', csrf_exempt(views.MessageView.as_view())),
    (r"^register/(\w+)/$", views.register)
)
