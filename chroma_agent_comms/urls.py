# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.conf.urls import url
import chroma_agent_comms.views as views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    url(r"^message/$", csrf_exempt(views.MessageView.as_view())),
    url(r"^register/(\w+)/$", views.register),
    url(r"^setup/(\w+)/$", views.setup),
    url(r"^reregister/$", views.reregister),
]
