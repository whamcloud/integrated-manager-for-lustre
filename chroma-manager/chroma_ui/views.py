#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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
from chroma_api.power_control import PowerControlTypeResource
from chroma_core.lib.service_config import SupervisorStatus
from chroma_core.lib.service_config import ServiceConfig

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers import json as django_json
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import auth
from django.http import HttpRequest

from chroma_core.models import UserProfile
from django.db.models import Q

from chroma_api.filesystem import FilesystemResource
from chroma_api.host import HostResource, ServerProfileResource
from chroma_api.target import TargetResource
from chroma_api.session import SessionResource
import settings
import simplejson


def _build_cache(request):
    cache = {}

    http_request = HttpRequest()
    http_request.META['HTTP_ACCEPT'] = 'application/json, text/plain, */*'
    http_request.user = request.user
    http_request.session = request.session

    http_response = SessionResource().get_list(http_request)

    resources = [
        FilesystemResource,
        TargetResource,
        HostResource,
        PowerControlTypeResource,
        ServerProfileResource
    ]
    for resource in resources:
        if settings.ALLOW_ANONYMOUS_READ or request.user.is_authenticated():
            resource_instance = resource()

            to_be_serialized = defaultdict(list)
            to_be_serialized['objects'] = [resource_instance.full_dehydrate(resource_instance.build_bundle(obj=m)) for m in
                                           resource.Meta.queryset._clone()]
            to_be_serialized = resource_instance.alter_list_data_to_serialize(request, to_be_serialized)

            cache[resource.Meta.resource_name] = [bundle.data for bundle in to_be_serialized['objects']]
        else:
            cache[resource.Meta.resource_name] = []

    from tastypie.serializers import Serializer

    serializer = Serializer()

    cache['session'] = simplejson.loads(http_response.content)

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


def _check_for_problems(request):
    if not ServiceConfig().configured():
        return render_to_response("installation.html",
                                  RequestContext(request, {}))
    else:
        try:
            stopped_services = SupervisorStatus().get_non_running_services()
        except socket.error:
            # Get a socket.error if we can't talk to supervisor at all
            stopped_services = ['supervisor']

        if stopped_services:
            # If any services are not running, stop here: rendering API resources
            # may depend on access to backend services, and in any case a non-running
            # service is a serious problem that must be reported.
            return render_to_response("backend_error.html", RequestContext(request, {
                'description': "The following services are not running: \n%s\n" % "\n".join(
                    [" * %s" % svc for svc in stopped_services]),
                'debug_info': _debug_info(request)
            }))


def _render_template_or_error(template_name, request):
    try:
        cache = json.dumps(_build_cache(request), cls=django_json.DjangoJSONEncoder)
    except:
        # An exception here indicates an internal error (bug or fatal config problem)
        # in any of the chroma_api resource classes
        return render_to_response("backend_error.html", RequestContext(request, {
            'description': "Exception rendering resources: %s" % traceback.format_exc(),
            'debug_info': _debug_info(request)
        }))

    return render_to_response(template_name, RequestContext(request, {'cache': cache}))


@ensure_csrf_cookie
def login(request):
    """
        Serves a login page, checking for problems first.
        If the user is already authenticated and the eula is accepted, redirects to index page.
        If the user is already authenticated and the eula is not accepted, logs the user out.
    """

    if request.user.is_authenticated():
        state = request.user.get_profile().get_state()

        if state == UserProfile.PASS:
            return HttpResponseRedirect(reverse(index))
        else:
            auth.logout(request)

    problem = _check_for_problems(request)

    if problem:
        return problem

    return _render_template_or_error("new/login.html", request)


def index(request):
    """
        Serve either the javascript UI, an advice HTML page
        if the backend isn't ready yet, or a blocking error page
        if the backend is in a bad state.

        Alternatively redirect to login if the user is not
        authenticated and anonymous users are forbidden.
    """

    if not request.user.is_authenticated() and not settings.ALLOW_ANONYMOUS_READ:
        return HttpResponseRedirect(reverse(login))

    problem = _check_for_problems(request)

    if problem:
        return problem

    return _render_template_or_error("new/index.html", request)


def old_index(request):
    """
        Serve either the javascript UI, an advice HTML page
        if the backend isn't ready yet, or a blocking error page
        if the backend is in a bad state.

        Alternatively redirect to login if the user is not
        authenticated and anonymous users are forbidden.
    """

    if not request.user.is_authenticated() and not settings.ALLOW_ANONYMOUS_READ:
        return HttpResponseRedirect(reverse(login))

    problem = _check_for_problems(request)

    if problem:
        return problem

    return _render_template_or_error("base.html", request)


def old_index_fs_user(request):
    """
        Serve either the javascript UI, an advice HTML page
        if the backend isn't ready yet, or a blocking error page
        if the backend is in a bad state.

        Alternatively redirect to login if the user is not
        authenticated and anonymous users are forbidden.
    """

    if not request.user.is_authenticated() and not settings.ALLOW_ANONYMOUS_READ:
        return HttpResponseRedirect(reverse(login))

    if not request.user.groups.filter(
        Q(name='filesystem_users') | Q(name='filesystem_administrators') | Q(name='superusers')).exists():
        return HttpResponseRedirect(reverse(index))

    problem = _check_for_problems(request)

    if problem:
        return problem

    return _render_template_or_error("base.html", request)


def old_index_fs_admin(request):
    """
        Serve either the javascript UI, an advice HTML page
        if the backend isn't ready yet, or a blocking error page
        if the backend is in a bad state.

        Alternatively redirect to login if the user is not
        authenticated and anonymous users are forbidden.
    """

    if not request.user.is_authenticated() and not settings.ALLOW_ANONYMOUS_READ:
        return HttpResponseRedirect(reverse(login))

    if not request.user.groups.filter(Q(name='filesystem_administrators') | Q(name='superusers')).exists():
        return HttpResponseRedirect(reverse(index))

    problem = _check_for_problems(request)

    if problem:
        return problem

    return _render_template_or_error("base.html", request)
