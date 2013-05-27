#!/usr/bin/env python
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
