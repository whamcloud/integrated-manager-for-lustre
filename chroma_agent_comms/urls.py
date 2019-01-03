# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.conf.urls import patterns
import chroma_agent_comms.views as views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = patterns(
    "",
    (r"^message/$", csrf_exempt(views.MessageView.as_view())),
    (r"^copytool_event/$", csrf_exempt(views.CopytoolEventView.as_view())),
    (r"^register/(\w+)/$", views.register),
    (r"^setup/(\w+)/$", views.setup),
    (r"^reregister/$", views.reregister),
)
