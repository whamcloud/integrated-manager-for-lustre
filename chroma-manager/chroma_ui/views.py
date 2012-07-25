#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import datetime

from django.shortcuts import render_to_response
from django.template import RequestContext

from chroma_api.filesystem import FilesystemResource
from chroma_api.host import HostResource
from chroma_api.target import TargetResource
import settings


def _build_cache(request):
    cache = {}
    resources = [
        FilesystemResource,
        TargetResource,
        HostResource
    ]
    for resource in resources:
        if settings.ALLOW_ANONYMOUS_READ or request.user.is_authenticated():
            resource_instance = resource()
            cache[resource.Meta.resource_name] = [resource_instance.full_dehydrate(resource_instance.build_bundle(obj = m)).data for m in resource.Meta.queryset._clone()]
        else:
            cache[resource.Meta.resource_name] = []

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
                RequestContext(request,
                        {'cache': json.dumps(_build_cache(request), cls = django_json.DjangoJSONEncoder),
                         'server_time': datetime.datetime.utcnow(),
                         'BUILD': settings.BUILD,
                         'VERSION': settings.VERSION,
                         'IS_RELEASE': settings.IS_RELEASE
                         }))
