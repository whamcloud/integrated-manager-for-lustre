# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.conf.urls import url, include

import chroma_api.urls
import chroma_agent_comms.urls

urlpatterns = [url(r"^agent/", include(chroma_agent_comms.urls)), url(r"^", include(chroma_api.urls))]
