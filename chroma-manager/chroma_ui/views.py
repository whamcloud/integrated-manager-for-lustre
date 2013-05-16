#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from collections import defaultdict

import json
import datetime
import socket
import traceback
import os
from chroma_core.lib.service_config import SupervisorStatus
from chroma_core.lib.service_config import ServiceConfig

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers import json as django_json

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
#            cache[resource.Meta.resource_name] = [
#                resource_instance.full_dehydrate(resource_instance.build_bundle(obj=m)).data for m in
#                resource.Meta.queryset._clone()]

            to_be_serialized = defaultdict(list)
            to_be_serialized['objects'] = [resource_instance.full_dehydrate(resource_instance.build_bundle(obj=m))  for m in
                                           resource.Meta.queryset._clone()]
            to_be_serialized = resource_instance.alter_list_data_to_serialize(request, to_be_serialized)

            cache[resource.Meta.resource_name] = [bundle.data for bundle in to_be_serialized['objects']]
        else:
            cache[resource.Meta.resource_name] = []

    from tastypie.serializers import Serializer

    serializer = Serializer()
    return serializer.to_simple(cache, {})


def _debug_info(request):
    """
    Return some information which may be useful to support in diagnosing errors

    :return: A list of two-tuples
    """

    info = {
        'server_time': "%s +00:00" % datetime.datetime.utcnow(),
        'BUILD': settings.BUILD,
        'VERSION': settings.VERSION,
        'IS_RELEASE': settings.IS_RELEASE,
        'fqdn': socket.getfqdn()
    }

    for k, v in zip(('sysname', 'nodename', 'release', 'version', 'machine'), os.uname()):
        info["uname_%s" % k] = v

    return sorted(info.items(), key=lambda v: v[0])


def index(request):
    """Serve either the javascript UI, an advice HTML page
    if the backend isn't ready yet, or a blocking error page
    if the backend is in a bad state."""

    if not ServiceConfig().configured():
        return render_to_response("installation.html",
                                  RequestContext(request, {}))
    else:
        stopped_services = SupervisorStatus().get_non_running_services()
        if stopped_services:
            # If any services are not running, stop here: rendering API resources
            # may depend on access to backend services, and in any case a non-running
            # service is a serious problem that must be reported.
            return render_to_response("backend_error.html", RequestContext(request, {
                'description': "The following services are not running: \n%s\n" % "\n".join(
                    [" * %s" % svc for svc in stopped_services]),
                'debug_info': _debug_info(request)
            }))
        else:
            try:
                cache = json.dumps(_build_cache(request), cls=django_json.DjangoJSONEncoder)
            except:
                # An exception here indicates an internal error (bug or fatal config problem)
                # in any of the chroma_api resource classes
                return render_to_response("backend_error.html", RequestContext(request, {
                    'description': "Exception rendering resources: %s" % traceback.format_exc(),
                    'debug_info': _debug_info(request)
                }))

            return render_to_response("base.html",
                                      RequestContext(request,
                                                     {'cache': cache,
                                                      'server_time': datetime.datetime.utcnow(),
                                                      'BUILD': settings.BUILD,
                                                      'VERSION': settings.VERSION,
                                                      'IS_RELEASE': settings.IS_RELEASE
                                                     }))
