#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.shortcuts import render_to_response
from django.template import RequestContext


def index(request):
    """Serve either the javascript UI, or an advice HTML page
    if the backend isn't ready yet."""

    from chroma_core.lib.service_config import ServiceConfig
    if not ServiceConfig().configured():
        return render_to_response("installation.html",
                RequestContext(request, {}))
    else:
        return render_to_response("base.html",
                RequestContext(request, {}))
