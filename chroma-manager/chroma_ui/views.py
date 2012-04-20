#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json

from django.shortcuts import render_to_response
from django.template import RequestContext

from chroma_api.filesystem import FilesystemResource
from chroma_api.host import HostResource
from chroma_api.target import TargetResource


def _build_cache():
    cache = {}
    resources = [
        FilesystemResource,
        TargetResource,
        HostResource
    ]
    for resource in resources:
        r = resource()
        l = [r.full_dehydrate(r.build_bundle(obj = m)).data for m in resource.Meta.queryset._clone()]
        cache[resource.Meta.resource_name] = l

    from tastypie.serializers import Serializer
    serializer = Serializer()
    return serializer.to_simple(cache, {})


def index(request):
    """Serve either the javascript UI, or an advice HTML page
    if the backend isn't ready yet."""

    from chroma_core.lib.service_config import ServiceConfig
    if not ServiceConfig().configured():
        return render_to_response("installation.html",
                RequestContext(request, {}))
    else:

        from django.core.serializers import json as django_json
        return render_to_response("base.html",
                RequestContext(request, {'cache': json.dumps(_build_cache(), cls = django_json.DjangoJSONEncoder)}))
