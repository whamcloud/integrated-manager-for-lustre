# HYD-1074
# This file copied from tastypie
# https://github.com/toastdriven/django-tastypie.git
# Commit ID a4a9b4da5bade2cc91087d9febeb1ca6e8578bf6
# This single file has its own license agreement (below) inherited from the tastypie distribution.

# Copyright (c) 2010, Daniel Lindsley
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# * Neither the name of the tastypie nor the
# names of its contributors may be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL tastypie BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from urlparse import urlparse

from django.test.client import FakePayload, Client
from tastypie.serializers import Serializer


class TestApiClient(object):
    def __init__(self, serializer=None):
        """
        Sets up a fresh ``TestApiClient`` instance.

        If you are employing a custom serializer, you can pass the class to the
        ``serializer=`` kwarg.
        """
        self.client = Client()
        self.serializer = serializer

        if not self.serializer:
            self.serializer = Serializer()

    def get_content_type(self, short_format):
        """
        Given a short name (such as ``json`` or ``xml``), returns the full content-type
        for it (``application/json`` or ``application/xml`` in this case).
        """
        return self.serializer.content_types.get(short_format, "json")

    def get(self, uri, format="json", data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``GET`` request to the provided URI.

        Optionally accepts a ``data`` kwarg, which in the case of ``GET``, lets you
        send along ``GET`` parameters. This is useful when testing filtering or other
        things that read off the ``GET`` params. Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.get('/api/v1/entry/1/', data={'format': 'json', 'title__startswith': 'a', 'limit': 20, 'offset': 60})

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs["HTTP_ACCEPT"] = content_type

        # GET & DELETE are the only times we don't serialize the data.
        if data is not None:
            kwargs["data"] = data

        if authentication is not None:
            kwargs["HTTP_AUTHORIZATION"] = authentication

        return self.client.get(uri, **kwargs)

    def post(self, uri, format="json", data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``POST`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``POST`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.post('/api/v1/entry/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs["content_type"] = content_type

        if data is not None:
            kwargs["data"] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs["HTTP_AUTHORIZATION"] = authentication

        return self.client.post(uri, **kwargs)

    def put(self, uri, format="json", data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``PUT`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``PUT`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.put('/api/v1/entry/1/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs["content_type"] = content_type

        if data is not None:
            kwargs["data"] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs["HTTP_AUTHORIZATION"] = authentication

        return self.client.put(uri, **kwargs)

    def patch(self, uri, format="json", data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``PATCH`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``PATCH`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.patch('/api/v1/entry/1/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs["content_type"] = content_type

        if data is not None:
            kwargs["data"] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs["HTTP_AUTHORIZATION"] = authentication

        # This hurts because Django doesn't support PATCH natively.
        parsed = urlparse(uri)
        r = {
            "CONTENT_LENGTH": len(kwargs["data"]),
            "CONTENT_TYPE": content_type,
            "PATH_INFO": self.client._get_path(parsed),
            "QUERY_STRING": parsed[4],
            "REQUEST_METHOD": "PATCH",
            "wsgi.input": FakePayload(kwargs["data"]),
        }
        r.update(kwargs)
        return self.client.request(**r)

    def delete(self, uri, format="json", data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``DELETE`` request to the provided URI.

        Optionally accepts a ``data`` kwarg, which in the case of ``DELETE``, lets you
        send along ``DELETE`` parameters. This is useful when testing filtering or other
        things that read off the ``DELETE`` params. Example::

            from tastypie.test import TestApiClient
            client = TestApiClient()

            response = client.delete('/api/v1/entry/1/', data={'format': 'json'})

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs["content_type"] = content_type

        # GET & DELETE are the only times we don't serialize the data.
        if data is not None:
            kwargs["data"] = data

        if authentication is not None:
            kwargs["HTTP_AUTHORIZATION"] = authentication

        return self.client.delete(uri, **kwargs)
