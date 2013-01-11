#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import sys
import os
import requests
from urlparse import urljoin


class HttpRequests(object):
    def __init__(self, server_http_url = '', *args, **kwargs):
        self.server_http_url = server_http_url
        self.session = requests.session()
        self.session.headers = {"Accept": "application/json", "Content-type": "application/json"}
        self.session.verify = False

    def get(self, url, **kwargs):
        if 'data' in kwargs:
            kwargs['params'] = kwargs['data']
            del kwargs['data']
        response = self.session.get(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def post(self, url, body = None, **kwargs):
        if body and 'data' not in kwargs:
            kwargs['data'] = json.dumps(body)

        response = self.session.post(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def put(self, url, body = None, **kwargs):
        if body and 'data' not in kwargs:
            kwargs['data'] = json.dumps(body)

        response = self.session.put(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def delete(self, url, **kwargs):
        response = self.session.delete(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def request(self, method, url, **kwargs):
        response = self.session.request(
            method,
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)


# FIXME: in python-requests >= 1.0.x this class is redundant
# (the standard repsonse has .json and .ok)
class HttpResponse(requests.Response):
    def __init__(self, response, *args, **kwargs):
        super(HttpResponse, self).__init__(*args, **kwargs)
        self.__dict__.update(response.__dict__.copy())

    @property
    def json(self):
        if self.text == '[]':
            return []
        else:
            try:
                return json.loads(self.text)
            except ValueError:
                print "Bad JSON: %s" % self.text
                raise

    @property
    def successful(self):
        # TODO: Make better
        return 200 <= self.status_code < 300


class AuthorizedHttpRequests(HttpRequests):
    def __init__(self, username, password, *args, **kwargs):
        super(AuthorizedHttpRequests, self).__init__(*args, **kwargs)

        # Usually on our Intel laptops https_proxy is set, and needs to be unset for tests,
        # but let's not completely rule out the possibility that someone might want to run
        # the tests on a remote system using a proxy.
        if 'https_proxy' in os.environ:
            sys.stderr.write("Warning: Using proxy %s from https_proxy" % os.environ['https_proxy'] +
                             " environment variable, you probably don't want that\n")

        response = self.get("/api/session/")
        if not response.successful:
            if 'https_proxy' in os.environ:
                raise RuntimeError("Failed to open session (using proxy %s)" % (os.environ['https_proxy']))
            else:
                raise RuntimeError("Failed to open session")
        self.session.headers['X-CSRFToken'] = response.cookies['csrftoken']
        self.session.cookies['csrftoken'] = response.cookies['csrftoken']
        self.session.cookies['sessionid'] = response.cookies['sessionid']

        response = self.post("/api/session/", data = json.dumps({'username': username, 'password': password}))
        if not response.successful:
            raise RuntimeError("Failed to authenticate")
