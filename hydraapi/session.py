#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydraapi.requesthandler import RequestHandler
from hydraapi.requesthandler import APIResponse

import django.contrib.auth as auth


class Handler(RequestHandler):
    def post(self, request, username, password):
        """Authenticate a session using username + password authentication"""
        user = auth.authenticate(username = username, password = password)
        if not user:
            return APIResponse("Login failed", 403)
        elif not user.is_active:
            return APIResponse("Account disabled", 403)

        auth.login(request, user)

    def delete(self, request):
        """Flush a session (log out)"""
        auth.logout(request)

    def get(self, request):
        """Dictionary of session objects (esp. any logged in user)"""
        # Calling get_token to ensure outgoing responses
        # get a csrftoken cookie appended by CsrfViewMiddleware
        import django.middleware.csrf
        django.middleware.csrf.get_token(request)

        user = request.user
        if not user.is_authenticated():
            # Anonymous user
            return {"user": None}
        else:
            # Authenticated user
            return {"user": {"id": user.id, "username": user.username}}
