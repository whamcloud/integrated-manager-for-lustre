#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import requests
from urlparse import urljoin


class HttpRequests(object):
    def __init__(self, server_http_url = '', *args, **kwargs):
        self.server_http_url = server_http_url
        self.session = requests.session(headers = {"Accept": "application/json", "Content-type": "application/json"})

    def get(self, url, **kwargs):
        response = self.session.get(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def post(self, url, body = None, **kwargs):
        if body and 'data' not in kwargs:
            kwargs['data'] = json.dumps(body)

        response = self.session.request(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def put(self, url, **kwargs):
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

        response = self.get("/api/session/")
        if not response.successful:
            raise RuntimeError("Failed to open session")
        self.session.headers['X-CSRFToken'] = response.cookies['csrftoken']
        self.session.cookies['csrftoken'] = response.cookies['csrftoken']
        self.session.cookies['sessionid'] = response.cookies['sessionid']

        response = self.post("/api/session/", data = json.dumps({'username': username, 'password': password}))
        if not response.successful:
            raise RuntimeError("Failed to authenticate")
