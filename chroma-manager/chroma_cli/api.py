#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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
from urlparse import urljoin

from chroma_cli.exceptions import InvalidApiResource, UnsupportedFormat, NotFound, TooManyMatches, BadRequest, InternalError, UnauthorizedRequest, AuthenticationFailure, ApiConnectionError


DEFAULT_API_URL = "https://localhost/api/"


class JsonSerializer(object):
    """
    Simple JSON serializer which implements the important parts of TastyPie's Serializer API.
    """
    formats = ["json"]
    content_types = {
            'json': "application/json"
    }
    datetime_formatting = "iso-8601"

    def __init__(self, formats=None, content_types=None, datetime_formatting=None):
        self.supported_formats = []

        for format in self.formats:
            self.supported_formats.append(self.content_types[format])

    def serialize(self, bundle, format="application/json", options={}):
        if format != "application/json":
            raise UnsupportedFormat("Can't serialize '%s', sorry." % format)

        return json.dumps(bundle, sort_keys=True)

    def deserialize(self, content, format='application/json'):
        if format != "application/json":
            raise UnsupportedFormat("Can't deserialize '%s', sorry." % format)

        return json.loads(content)


class ChromaSessionClient(object):
    def __init__(self):
        self.is_authenticated = False
        self.api_uri = DEFAULT_API_URL

        import requests
        self.session = requests.session()
        self.session.headers = {'Accept': "application/json",
                                'Content-Type': "application/json"}
        # FIXME?: Should we be doing CA verification in the CLI?
        self.session.verify = False

    def __getattr__(self, method):
        return getattr(self.session, method)

    @property
    def session_uri(self):
        return urljoin(self.api_uri, "session/")

    def start_session(self):
        r = self.get(self.session_uri)
        if not 200 <= r.status_code < 300:
            raise RuntimeError("No session (status: %s, text: %s)" %
                               (r.status_code, r.content))

        self.session.headers['X-CSRFToken'] = r.cookies['csrftoken']
        self.session.cookies['csrftoken'] = r.cookies['csrftoken']
        self.session.cookies['sessionid'] = r.cookies['sessionid']

    def login(self, **credentials):
        if not self.is_authenticated:
            if 'sessionid' not in self.session.cookies:
                self.start_session()

            r = self.post(self.session_uri, data=json.dumps(credentials))
            if not 200 <= r.status_code < 300:
                raise AuthenticationFailure()
            else:
                self.is_authenticated = True

        return self.is_authenticated

    def logout(self):
        if self.is_authenticated:
            self.delete(self.session_uri)
            self.is_authenticated = False


class ApiClient(object):
    def __init__(self, serializer=None):
        self.client = ChromaSessionClient()
        self.serializer = serializer

        if not self.serializer:
            self.serializer = JsonSerializer()

    def get_content_type(self, short_format):
        return self.serializer.content_types.get(short_format,
                                                 'application/json')

    def get(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        if authentication and not self.client.is_authenticated:
            self.client.login(**authentication)

        return self.client.get(uri, headers=headers, params=data)

    def post(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        if authentication and not self.client.is_authenticated:
            self.client.login(**authentication)

        return self.client.post(uri, headers=headers,
                                data=self.serializer.serialize(data))

    def put(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        if authentication and not self.client.is_authenticated:
            self.client.login(**authentication)

        return self.client.put(uri, headers=headers,
                               data=self.serializer.serialize(data))

    def delete(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        if authentication and not self.client.is_authenticated:
            self.client.login(**authentication)

        return self.client.delete(uri, headers=headers, params=data)


class CommandMonitor(object):
    def __init__(self, api, cmd):
        self.api = api
        self.cmd = cmd

    def update(self, pause=1):
        import time
        time.sleep(pause)
        self.cmd = self.api.endpoints['command'].show(self.cmd['id'])

    @property
    def status(self):
        return {
            (True, False, False): "Finished",
            (True, True, False): "Canceled",
            (True, True, True): "Canceled due to error",
            (True, False, True): "Failed",
            (False, False, False): "Tasked",
            (False, True, False): "Canceling",
        }[(self.cmd['complete'], self.cmd['cancelled'], self.cmd['errored'])]

    @property
    def completed(self):
        return self.status in ["Finished", "Canceled", "Failed"]

    @property
    def incomplete_jobs(self):
        def _job_id(j_uri):
            import re
            m = re.search(r"(\d+)/?$", j_uri)
            if m:
                return m.group(1)
            else:
                return None

        incomplete = []
        for job_id in [_job_id(j_uri) for j_uri in self.cmd['jobs']]:
            job = self.api.endpoints['job'].show(job_id)
            if job['state'] != "complete":
                incomplete.append(int(job_id))

        return incomplete


class ApiHandle(object):
    # By default, we want to use our own ApiClient class.  This
    # provides a handle for the test framework to inject its own
    # ApiClient which uses Django's Client under the hood.
    ApiClient = ApiClient

    def __init__(self, api_uri=None, authentication=None):
        self.__schema = None
        self.base_url = self._fix_base_uri(api_uri)
        if not self.base_url:
            self.base_url = DEFAULT_API_URL
        self.authentication = authentication
        self.endpoints = ApiEndpointGenerator(self)
        self.serializer = JsonSerializer()
        self.api_client = self.ApiClient()
        # Ugh. Least-worst option, I think.
        self.api_client.client.api_uri = self.base_url
        self.command_monitor = lambda cmd: CommandMonitor(self, cmd)

    def _fix_base_uri(self, base_uri):
        """
        Clean up supplied API URI.

        >>> ah = ApiHandle()
        >>> ah.base_url
        'https://localhost/api/'
        >>> ah = ApiHandle(api_uri="http://some.server")
        >>> ah.base_url
        'http://some.server/api/'
        >>> ah = ApiHandle(api_uri="some.server")
        >>> ah.base_url
        'https://some.server/api/'
        >>> ah = ApiHandle(api_uri="http://localhost:8000/api/")
        >>> ah.base_url
        'http://localhost:8000/api/'
        """
        if not base_uri:
            return None

        import re
        if not re.search(r"^http(s)?://", base_uri):
            base_uri = "https://" + base_uri
        if not re.search(r"/api(/?)$", base_uri):
            base_uri = urljoin(base_uri, "/api/")

        return base_uri

    @property
    def schema(self):
        if not self.__schema:
            self.__schema = self.send_and_decode("get", "")

        return self.__schema

    def data_or_text(self, content):
        try:
            return self.serializer.deserialize(content)
        except ValueError:
            return content

    def send_and_decode(self, method_name, relative_url, data=None):
        full_url = urljoin(self.base_url, relative_url)

        from requests import ConnectionError
        method = getattr(self.api_client, method_name)
        try:
            r = method(full_url, data=data)
        except ConnectionError:
            raise ApiConnectionError(self.base_url)

        if r.status_code == 401:
            # Try logging in and retry the request
            self.api_client.client.login(**self.authentication)
            r = method(full_url, data=data)

        decoded = self.data_or_text(r.content)
        if 200 <= r.status_code < 304:
            return decoded
        elif r.status_code == 400:
            raise BadRequest(decoded)
        elif r.status_code == 401:
            raise UnauthorizedRequest(decoded)
        elif r.status_code == 404:
            try:
                raise NotFound(decoded['error_message'])
            except (KeyError, TypeError):
                raise NotFound("Not found (%s)" % decoded)
        elif r.status_code == 500:
            try:
                raise InternalError(decoded['traceback'])
            except KeyError:
                raise InternalError("Unknown server error: %s" % decoded)
        else:
            raise RuntimeError("status: %s, text: %s" % (r.status_code,
                                                         r.content))


class ApiEndpointGenerator(object):
    """
    Emulate a dict of resource -> endpoint pairs, but only as much as
    necessary.

    Doesn't implement the full dict API, so beware.
    """
    def __init__(self, api):
        self.api = api
        self.endpoints = {}

    def keys(self):
        return self.api.schema.keys()

    def _load_endpoints(self):
        for resource in self.keys():
            if resource not in self.endpoints:
                self.endpoints[resource] = ApiEndpoint(self.api, resource)

    def values(self):
        self._load_endpoints()
        return self.endpoints.values()

    def items(self):
        self._load_endpoints()
        return self.endpoints.items()

    def __getitem__(self, resource_name):
        if resource_name not in self.endpoints:
            if resource_name in self.api.schema:
                self.endpoints[resource_name] = ApiEndpoint(self.api,
                                                            resource_name)
            else:
                raise InvalidApiResource(resource_name)

        return self.endpoints[resource_name]


class ApiEndpoint(object):
    def __init__(self, handle, name):
        self.__schema = None
        self.api_handle = handle
        self.name = name

        import chroma_cli.api_resource
        try:
            self.resource_klass = getattr(chroma_cli.api_resource,
                                          self.resource_klass_name)
        except AttributeError:
            # generic fallback
            self.resource_klass = chroma_cli.api_resource.ApiResource

    @property
    def resource_klass_name(self):
        return "".join([part.capitalize() for part in self.name.split("_")])

    @property
    def schema(self):
        if not self.__schema:
            schema_url = self.api_handle.schema[self.name]['schema']
            self.__schema = self.api_handle.send_and_decode("get", schema_url)

        return self.__schema

    @property
    def uri(self):
        return self.api_handle.schema[self.name]['list_endpoint']

    @property
    def fields(self):
        return self.schema['fields']

    def resolve_uri(self, query):
        try:
            # Slight hack here -- relies on the "name" field usually being
            # first in a reverse-sort in order to optimize for the most
            # common query.
            for field, expressions in (
                    sorted(self.schema['filtering'].iteritems(),
                           key=lambda x: x[0], reverse=True)):
                for expression in expressions:
                    filter = "%s__%s" % (field, expression)

                    try:
                        candidates = self.list(**{filter: query})
                    except BadRequest:
                        continue

                    if len(candidates) > 1:
                        if expression in ["startswith", "endswith"]:
                            raise TooManyMatches("The query %s/%s matches more than one resource: %s" % (self.name, query, candidates))
                        else:
                            continue

                    try:
                        if query in candidates[0][field]:
                            return candidates[0]['resource_uri']
                    except (IndexError, KeyError):
                        continue
        except KeyError:
            # No filtering possible?
            pass

        raise NotFound("Unable to resolve URI for %s/%s" % (self.name, query))

    def resource_uri(self, subject):
        try:
            id = int(subject)
            return urljoin(self.uri, "%s/" % id)
        except (ValueError, TypeError):
            return urljoin(self.uri, self.resolve_uri(subject))

    def get_decoded(self, uri=None, **data):
        if not uri:
            uri = self.uri
        return self.api_handle.send_and_decode("get", uri, data=data)

    def list(self, **data):
        resources = []
        try:
            for object in self.get_decoded(**data)['objects']:
                resources.append(self.resource_klass(**object))
        except ValueError:
            pass
        return resources

    def show(self, subject):
        object = self.get_decoded(self.resource_uri(subject))
        return self.resource_klass(**object)

    def create(self, **data):
        return self.api_handle.send_and_decode("post", self.uri, data=data)

    def delete(self, subject):
        return self.api_handle.send_and_decode("delete",
                                               self.resource_uri(subject))

    def update(self, subject, **data):
        return self.api_handle.send_and_decode("put",
                                               self.resource_uri(subject),
                                               data=data)

    def get(self, uri=None, **kwargs):
        """
        Expose a "raw" get() with no error handling or decoding.
        """
        if not uri:
            from urlparse import urljoin
            uri = urljoin(self.api_handle.base_url, self.uri)
        return self.api_handle.api_client.get(uri, **kwargs)
