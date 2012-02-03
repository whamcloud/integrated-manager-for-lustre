#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json
import requests
from urlparse import urljoin


class AuthorizedHttpRequests(object):
    def __init__(self, username, password, *args, **kwargs):
        super(self, AuthorizedHttpRequests).__init__(*args, **kwargs)

        response = self.get("/api/session/", data = {'username': 'admin', 'password': 'password'})
        self.assertEqual(response.successful, True)
        self.session.headers['X-CSRFToken'] = response.cookies['csrftoken']
        self.session.cookies['csrftoken'] = response.cookies['csrftoken']
        self.session.cookies['sessionid'] = response.cookies['sessionid']

        response = self.post("/api/session/", data = {'username': username, 'password': password})
        self.assertEqual(response.successful, True)


class HttpRequests(object):
    def __init__(self, server_http_url = '', *args, **kwargs):
        self.server_http_url = server_http_url
        self.session = requests.session()

    def get(self, url, **kwargs):
        response = self.session.get(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def post(self, url, **kwargs):
        response = self.session.post(
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
            return json.loads(self.text)

    @property
    def successful(self):
        # TODO: Make better
        return 200 <= self.status_code < 300
