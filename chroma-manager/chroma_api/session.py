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


import settings

import django.contrib.auth as auth

from chroma_api.authentication import CsrfAuthentication
from tastypie.authorization import Authorization
from tastypie.resources import Resource
from tastypie import fields
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse


class Session:
    def __init__(self, user = None):
        self.user = user
        if settings.ALLOW_ANONYMOUS_READ:
            self.read_enabled = True
        else:
            self.read_enabled = (user != None)


class SessionResource(Resource):
    """
    The current user session.  This resource exposes only list-style methods,
    all of which implicitly operate on the current session (determined from
    HTTP headers).

    In addition to finding out about who is logged in, GET operations on the
    session resource are a useful way of obtaining ``sessionid`` and ``csrftoken``
    values (see `Access control <#access-control>`_)

    Authenticate a session by using POST to send credentials. Use DELETE to log out from a session.
    """
    user = fields.ToOneField('chroma_api.user.UserResource', 'user', full = True, null = True,
                             help_text = "A user object")
    read_enabled = fields.BooleanField(
        attribute = 'read_enabled',
        help_text = "If ``true``, the current session is permitted to do GET operations\
        on other API resources.  Always true for authenticated users, depends on \
        settings for anonymous users.")

    class Meta:
        object_class = Session
        # Use CsrfAuthentication instead of AnonymousAuthorization
        # because even un-logged-in users always need to access this
        # in order to be able to log in
        authentication = CsrfAuthentication()
        # Use pass-through authorization instead of django authorization
        # because an un-logged-in user needs to have access to GET and POST
        # (and access to DELETE is harmless because it implicitly refers
        # only to the session of the caller)
        authorization = Authorization()
        list_allowed_methods = ['get', 'post', 'delete']
        detail_allowed_methods = []
        resource_name = 'session'

    def get_resource_uri(self, bundle):
        return self.get_resource_list_uri()

    def obj_create(self, bundle, request = None, **kwargs):
        """Authenticate a session using username + password authentication"""
        username = bundle.data['username']
        password = bundle.data['password']

        user = auth.authenticate(username = username, password = password)
        if not user:
            raise ImmediateHttpResponse(response=http.HttpForbidden())
        elif not user.is_active:
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        auth.login(request, user)

    def delete_list(self, request = None, **kwargs):
        """Log out this session"""
        auth.logout(request)

    def get_list(self, request = None, **kwargs):
        """Dictionary of session objects (esp. any logged in user).

        This method also always includes a session and CSRF cookie,
        so it can be used by clients to set up a session before
        authenticating.
        """
        # Calling get_token to ensure outgoing responses
        # get a csrftoken cookie appended by CsrfViewMiddleware
        import django.middleware.csrf
        django.middleware.csrf.get_token(request)

        # Force a session Set-Cookie in the response
        request.session.modified = True

        user = request.user
        if not user.is_authenticated():
            # Anonymous user
            user = None
        bundle = self.build_bundle(obj = Session(user), request = request)
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)
