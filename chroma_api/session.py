# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import settings

from collections import defaultdict

import django.contrib.auth as auth

from chroma_api.authentication import CsrfAuthentication, AnonymousAuthentication
from chroma_api.validation_utils import validate
from tastypie.authorization import Authorization, ReadOnlyAuthorization
from tastypie.resources import Resource
from tastypie import fields
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.validation import Validation


class Session:
    def __init__(self, user=None):
        self.user = user
        if settings.ALLOW_ANONYMOUS_READ:
            self.read_enabled = True
        else:
            self.read_enabled = user is not None


class SessionValidation(Validation):
    """
    Validates user credentials
    """

    def is_valid(self, bundle, request=None):
        errors = defaultdict(list)

        def check_field_exists(field_name):
            """
            Check the field has been populated.
            If not add it to the errors dict.
            """
            field = bundle.data.get(field_name, "").strip()

            if not field:
                errors[field_name].append("This field is mandatory")

        if request.method != "POST":
            return errors

        check_field_exists("username")
        check_field_exists("password")

        return errors


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

    user = fields.ToOneField("chroma_api.user.UserResource", "user", full=True, null=True, help_text="A user object")
    read_enabled = fields.BooleanField(
        attribute="read_enabled",
        help_text="If ``true``, the current session is permitted to do GET operations\
        on other API resources.  Always true for authenticated users, depends on \
        settings for anonymous users.",
    )

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
        list_allowed_methods = ["get", "post", "delete"]
        detail_allowed_methods = []
        resource_name = "session"
        validation = SessionValidation()

    def get_resource_uri(self, bundle=None, url_name=None):
        return Resource.get_resource_uri(self)

    @validate
    def obj_create(self, bundle, **kwargs):
        request = bundle.request
        """Authenticate a session using username + password authentication"""
        username = bundle.data["username"]
        password = bundle.data["password"]

        user = auth.authenticate(username=username, password=password)
        if not user or not user.is_active:
            error = {"__all__": "Authentication Failed."}
            resp = self.create_response(request, error, response_class=http.HttpForbidden)
            raise ImmediateHttpResponse(response=resp)

        auth.login(request, user)

    def delete_list(self, request=None, **kwargs):
        """Log out this session"""
        auth.logout(request)

    def get_list(self, request=None, **kwargs):
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
        bundle = self.build_bundle(obj=Session(user), request=request)
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)


class Auth:
    def __init__(self, user=None):
        self.user = user


class Noop:
    pass


class AnonAuthResource(Resource):
    """
    Success / failure of current session being existant
    """

    class Meta:
        class_object = Noop
        authentication = AnonymousAuthentication()
        authorization = ReadOnlyAuthorization()
        list_allowed_methods = ["get"]
        detail_allowed_methods = []
        resource_name = "anon_auth"

    def get_resource_uri(self, bundle=None, url_name=None):
        return Resource.get_resource_uri(self)

    def get_list(self, request=None, **kwargs):
        bundle = self.build_bundle(obj=Noop(), request=request)
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)


class AuthResource(Resource):
    """
    Success / failure of current session being existant
    """

    user = fields.ToOneField("chroma_api.user.UserResource", "user", full=True, null=True, help_text="A user object")

    class Meta:
        class_object = Auth
        authentication = AnonymousAuthentication()
        authorization = ReadOnlyAuthorization()
        list_allowed_methods = ["get"]
        detail_allowed_methods = []
        resource_name = "auth"

    def get_resource_uri(self, bundle=None, url_name=None):
        return Resource.get_resource_uri(self)

    def get_list(self, request=None, **kwargs):
        """Dictionary of session objects (esp. any logged in user).

        This method also always includes a session and CSRF cookie,
        so it can be used by clients to set up a session before
        authenticating.
        """
        # Calling get_token to ensure outgoing responses
        # get a csrftoken cookie appended by CsrfViewMiddleware
        import django.middleware.csrf

        django.middleware.csrf.get_token(request)

        user = request.user
        if not user.is_authenticated():
            error = {"__all__": "Authentication Failed."}
            resp = self.create_response(request, error, response_class=http.HttpUnauthorized)
            raise ImmediateHttpResponse(response=resp)

        bundle = self.build_bundle(obj=Auth(user), request=request)
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)
