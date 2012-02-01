#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json
import requests
from urlparse import urljoin


class HttpRequests(object):

    def __init__(self, server_http_url = '', *args, **kwargs):
        self.server_http_url = server_http_url

    def get(self, url, **kwargs):
        response = requests.get(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def post(self, url, **kwargs):
        response = requests.post(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def put(self, url, **kwargs):
        response = requests.put(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def delete(self, url, **kwargs):
        response = requests.delete(
            urljoin(self.server_http_url, url),
            **kwargs
        )

        return HttpResponse(response)

    def request(self, method, url, **kwargs):
        response = requests.request(
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
        return 200 <= self.status_code < 300 and self.json is not None
