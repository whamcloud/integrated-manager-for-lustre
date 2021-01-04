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


import time
import contextlib
import itertools

from django.conf import settings
from django.db import connection
from tastypie.serializers import Serializer

from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from tests.unit.chroma_core.helpers.test_api_client import TestApiClient


class ResourceTestCase(IMLUnitTestCase):
    """
    A useful base class for the start of testing Tastypie APIs.
    """

    def setUp(self):
        super(ResourceTestCase, self).setUp()
        self.serializer = Serializer()
        self.api_client = TestApiClient()

    def get_credentials(self):
        """
        A convenience method for the user as a way to shorten up the
        often repetitious calls to create the same authentication.

        Raises ``NotImplementedError`` by default.

        Usage::

            class MyResourceTestCase(ResourceTestCase):
                def get_credentials(self):
                    return self.create_basic('daniel', 'pass')

                # Then the usual tests...

        """
        raise NotImplementedError("You must return the class for your Resource to test.")

    def create_basic(self, username, password):
        """
        Creates & returns the HTTP ``Authorization`` header for use with BASIC
        Auth.
        """
        import base64

        return "Basic %s" % base64.b64encode(":".join([username, password]))

    def create_apikey(self, username, api_key):
        """
        Creates & returns the HTTP ``Authorization`` header for use with
        ``ApiKeyAuthentication``.
        """
        return "ApiKey %s:%s" % (username, api_key)

    def create_digest(self, username, api_key, method, uri):
        """
        Creates & returns the HTTP ``Authorization`` header for use with Digest
        Auth.
        """
        from tastypie.authentication import hmac, sha1, uuid, python_digest

        new_uuid = uuid.uuid4()
        opaque = hmac.new(str(new_uuid), digestmod=sha1).hexdigest()
        return python_digest.build_authorization_request(
            username,
            method.upper(),
            uri,
            1,  # nonce_count
            digest_challenge=python_digest.build_digest_challenge(
                time.time(), getattr(settings, "SECRET_KEY", ""), "django-tastypie", opaque, False
            ),
            password=api_key,
        )

    def create_oauth(self, user):
        """
        Creates & returns the HTTP ``Authorization`` header for use with Oauth.
        """
        from oauth_provider.models import Consumer, Token, Resource

        # Necessary setup for ``oauth_provider``.
        resource, _ = Resource.objects.get_or_create(url="test", defaults={"name": "Test Resource"})
        consumer, _ = Consumer.objects.get_or_create(key="123", defaults={"name": "Test", "description": "Testing..."})
        token, _ = Token.objects.get_or_create(
            key="foo",
            token_type=Token.ACCESS,
            defaults={"consumer": consumer, "resource": resource, "secret": "", "user": user},
        )

        # Then generate the header.
        oauth_data = {
            "oauth_consumer_key": "123",
            "oauth_nonce": "abc",
            "oauth_signature": "&",
            "oauth_signature_method": "PLAINTEXT",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": "foo",
        }
        return "OAuth %s" % ",".join([key + "=" + value for key, value in oauth_data.items()])

    def assertHttpOK(self, resp):
        """
        Ensures the response is returning a HTTP 200.
        """
        return self.assertEqual(resp.status_code, 200, resp.content)

    def assertHttpCreated(self, resp):
        """
        Ensures the response is returning a HTTP 201.
        """
        return self.assertEqual(resp.status_code, 201)

    def assertHttpAccepted(self, resp):
        """
        Ensures the response is returning either a HTTP 202 or a HTTP 204.
        """
        return self.assertTrue(
            resp.status_code in [202, 204], "Expected 202 or 204 status code, got %s" % resp.status_code
        )

    def assertHttpNoContent(self, resp):
        """
        Ensures the response is returning a HTTP 204.
        """
        return self.assertEqual(resp.status_code, 204)

    def assertHttpMultipleChoices(self, resp):
        """
        Ensures the response is returning a HTTP 300.
        """
        return self.assertEqual(resp.status_code, 300)

    def assertHttpSeeOther(self, resp):
        """
        Ensures the response is returning a HTTP 303.
        """
        return self.assertEqual(resp.status_code, 303)

    def assertHttpNotModified(self, resp):
        """
        Ensures the response is returning a HTTP 304.
        """
        return self.assertEqual(resp.status_code, 304)

    def assertHttpBadRequest(self, resp):
        """
        Ensures the response is returning a HTTP 400.
        """
        return self.assertEqual(resp.status_code, 400)

    def assertHttpUnauthorized(self, resp):
        """
        Ensures the response is returning a HTTP 401.
        """
        return self.assertEqual(resp.status_code, 401)

    def assertHttpForbidden(self, resp):
        """
        Ensures the response is returning a HTTP 403.
        """
        return self.assertEqual(resp.status_code, 403)

    def assertHttpNotFound(self, resp):
        """
        Ensures the response is returning a HTTP 404.
        """
        return self.assertEqual(resp.status_code, 404)

    def assertHttpMethodNotAllowed(self, resp):
        """
        Ensures the response is returning a HTTP 405.
        """
        return self.assertEqual(resp.status_code, 405)

    def assertHttpConflict(self, resp):
        """
        Ensures the response is returning a HTTP 409.
        """
        return self.assertEqual(resp.status_code, 409)

    def assertHttpGone(self, resp):
        """
        Ensures the response is returning a HTTP 410.
        """
        return self.assertEqual(resp.status_code, 410)

    def assertHttpTooManyRequests(self, resp):
        """
        Ensures the response is returning a HTTP 429.
        """
        return self.assertEqual(resp.status_code, 429)

    def assertHttpApplicationError(self, resp):
        """
        Ensures the response is returning a HTTP 500.
        """
        return self.assertEqual(resp.status_code, 500)

    def assertHttpNotImplemented(self, resp):
        """
        Ensures the response is returning a HTTP 501.
        """
        return self.assertEqual(resp.status_code, 501)

    def assertValidJSON(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid JSON &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_json(data)

    def assertValidXML(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid XML &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_xml(data)

    def assertValidYAML(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid YAML &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_yaml(data)

    def assertValidPlist(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid
        binary plist & can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_plist(data)

    def assertValidJSONResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/json``)
        * The content is valid JSON
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp["Content-Type"].startswith("application/json"))
        self.assertValidJSON(resp.content)

    def assertValidXMLResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/xml``)
        * The content is valid XML
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp["Content-Type"].startswith("application/xml"))
        self.assertValidXML(resp.content)

    def assertValidYAMLResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``text/yaml``)
        * The content is valid YAML
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp["Content-Type"].startswith("text/yaml"))
        self.assertValidYAML(resp.content)

    def assertValidPlistResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/x-plist``)
        * The content is valid binary plist data
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp["Content-Type"].startswith("application/x-plist"))
        self.assertValidPlist(resp.content)

    def deserialize(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, this method
        checks the ``Content-Type`` header & attempts to deserialize the data based on
        that.

        It returns a Python datastructure (typically a ``dict``) of the serialized data.
        """
        format = resp["Content-Type"].split(";")[0]

        if format != "text/html":
            return self.serializer.deserialize(resp.content, format=format)
        else:
            return resp.content

    def serialize(self, data, format="application/json"):
        """
        Given a Python datastructure (typically a ``dict``) & a desired content-type,
        this method will return a serialized string of that data.
        """
        return self.serializer.serialize(data, format=format)

    def assertKeys(self, data, expected):
        """
        This method ensures that the keys of the ``data`` match up to the keys of
        ``expected``.

        It covers the (extremely) common case where you want to make sure the keys of
        a response match up to what is expected. This is typically less fragile than
        testing the full structure, which can be prone to data changes.
        """
        self.assertEqual(sorted(data.keys()), sorted(expected))

    @contextlib.contextmanager
    def assertQueries(self, *prefixes):
        "Assert the correct queries are efficiently executed for a block."

        debug = connection.use_debug_cursor
        connection.use_debug_cursor = True

        count = len(connection.queries)
        yield

        if type(prefixes[0]) == int:
            assert prefixes[0] == len(connection.queries[count:])
        else:
            for prefix, query in itertools.izip_longest(prefixes, connection.queries[count:]):
                assert prefix and query and query["sql"].startswith(prefix), (prefix, query)

        connection.use_debug_cursor = debug
