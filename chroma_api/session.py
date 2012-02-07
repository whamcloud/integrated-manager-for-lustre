#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import django.contrib.auth as auth

from chroma_api.authentication import CsrfAuthentication
from tastypie.authorization import Authorization
from tastypie.resources import Resource
from tastypie import fields
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse


class SessionResource(Resource):
    user = fields.DictField()

    class Meta:
        object_class = dict
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
            return self.create_response(request, {"user": None})
        else:
            # Authenticated user
            return self.create_response(request, {"user": {"id": user.id, "username": user.username}})
