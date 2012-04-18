#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import sys
import time

from chroma_cli.exceptions import BadRequest, InternalError

import requests
from urlparse import urljoin
import simplejson as json


class ApiClient(object):
    __schema = None

    def __init__(self, url, username=None, password=None):
        self.url = url

        self._session = requests.session(headers = {'Accept': "application/json", 'Content-Type': "application/json"})
        response = self._session.get(urljoin(self.url, "session/"))
        if not 200 <= response.status_code < 300:
            raise RuntimeError("Failed to open session")
        self._session.headers['X-CSRFToken'] = response.cookies['csrftoken']
        self._session.cookies['csrftoken'] = response.cookies['csrftoken']
        self._session.cookies['sessionid'] = response.cookies['sessionid']

        self.login(username, password)

    def handle_response(self, response):
        if 200 <= response.status_code < 304:
            return response.text
        elif response.status_code == 400:
            # A bad request -- deserialize the errors
            raise BadRequest(json.loads(response.text))
        elif response.status_code == 500:
            try:
                decoded = json.loads(response.text)
                raise InternalError(decoded['traceback'])
            except (ValueError, KeyError):
                raise InternalError("Malformed content: %s" % response.text)
        elif response.status_code == 404:
            raise AttributeError("No resource with that id")
        else:  # TODO: add more classes of reponse exceptions
            raise RuntimeError("status: %s, text: %s" % (response.status_code,
                                                         response.text))

    def login(self, username, password):
        response = self._session.post(urljoin(self.url, "session/"),
                                      data = json.dumps({'username': username,
                                                        'password': password}))
        if not 200 <= response.status_code < 300:
            raise RuntimeError("failed to authenticate")

    def get(self, url):
        response = self._session.get(urljoin(self.url, url))
        return json.loads(self.handle_response(response))

    def post(self, url, **kwargs):
        response = self._session.post(url, json.dumps(kwargs))
        return json.loads(self.handle_response(response))

    def delete(self, url, **kwargs):
        response = self._session.delete(url)
        return json.loads(self.handle_response(response))

    def put(self, url, **kwargs):
        response = self._session.put(url, json.dumps(kwargs))
        return json.loads(self.handle_response(response))

    def patch(self, url, **kwargs):
        raise NotImplementedError("No PATCH support (HYD-732)")

    @property
    def schema(self):
        if self.__schema is None:
            self.__schema = self.get(self.url)
        return self.__schema

    @property
    def resource_names(self):
        return sorted([str(name) for name in self.schema.keys()])

    def get_endpoint(self, name):
        return getattr(self, name)

    def __getattr__(self, attr):
        resource = self.schema[attr]
        return ApiResourceEndpoint(self,
                                   name = attr,
                                   url = urljoin(self.url,
                                                 resource['list_endpoint']),
                                   schema_url = urljoin(self.url,
                                                        resource['schema']))


class ApiResourceEndpoint(object):
    __schema = None

    def __init__(self, api, name, url, schema_url = None):
        self.api = api
        self.name = name
        self.url = url
        self.schema_url = schema_url

    def __getattr__(self, attr):
        # Fall through for properties without explicit methods.
        return self.schema[attr]

    @property
    def schema(self):
        if self.__schema is None:
            self.__schema = self.api.get(self.schema_url)
        return self.__schema

    @property
    def verbs(self):
        verbs = []
        for method in self.schema['allowed_detail_http_methods']:
            verbs.append({'get': "show",
                          'put': "update",
                          'post': None,
                          'patch': None,
                          'delete': "delete"}[method])

        for method in self.schema['allowed_list_http_methods']:
            verbs.append({'get': "list",
                          'put': None,
                          'delete': None,
                          'patch': None,
                          'post': "create"}[method])

        return [v for v in verbs if v != None]

    def objects(self, filters=None):
        qs_options = []

        qs_options.extend(filters)
        # TODO: Until we implement pagination support, there should
        # be no limit to the reponse list size. (HYD-725)
        qs_options.extend(["limit=0"])

        url = urljoin(self.url, "?%s" % "&".join(qs_options))
        data = self.api.get(url)
        return [ApiResource(self.name, self.api, **json_object)
                for json_object in data['objects']]

    def _build_filters(self, **kwargs):
        filters = []
        try:
            for name, expressions in self.schema['filtering'].items():
                if name in kwargs and kwargs[name] != None:
                    try:
                        if 'exact' in expressions:
                            filters.append("%s=%s" % (name, kwargs[name]))
                    except TypeError:
                        # ALL or ALL_WITH_EXPRESSIONS
                        filters.append("%s=%s" % (name, kwargs[name]))
                    # TODO: other kinds of filtering, including
                    # negation, ranges, etc. (HYD-730)
        except KeyError:
            pass
        return filters

    def _blob2objects(self, blob):
        objects = []

        # simple single resource blob
        if 'resource_uri' in blob.keys():
            objects.append(ApiResource(self.name, self.api, **blob))

        # complex blob
        if 'command' in blob.keys():
            objects.append(ApiCommandResource(self.name, self.api,
                                              **blob['command']))

        if 'resource' in blob.keys():
            objects.append(ApiResource(self.name, self.api,
                                       **blob['resource']))

        return objects

    def list(self, **kwargs):
        filters = self._build_filters(**kwargs)

        return self.objects(filters)

    def create(self, **kwargs):
        return self._blob2objects(self.api.post(self.url, **kwargs))

    def update(self, **kwargs):
        return self._blob2objects(self.api.put(urljoin(self.url,
                                                       "%s/" % kwargs['id']),
                                  **kwargs))

    def delete(self, **kwargs):
        return self._blob2objects(self.api.delete(urljoin(self.url,
                                                          "%s/" % kwargs['id']),
                                  **kwargs))

    def show(self, **kwargs):
        # show always returns a single object
        return self._blob2objects(self.api.get(urljoin(self.url,
                                                       "%s/" % kwargs['id'])))[0]


class ApiResource(object):
    __unprintable_keys = ["api", "resource_uri", "content_type_id",
                          "immutable_state", "resource"]

    def __init__(self, resource_name, api, **kwargs):
        self._data = {}

        # NB: Doing things this way is quite convenient, in that it allows
        # us to ask a resource naturally for the value a field as an attribute,
        # e.g. resource.available_transitions.
        # When adding methods to ApiResource and its subclasses, care
        # must be taken to choose method names which are highly
        # unlikely to conflict with field names.
        for key, val in kwargs.items():
            assert key[0] != '_', "field names may not start with '_': %s" % key
            assert not hasattr(self, key), "field name conflicts with existing attribute: %s" % key
            self._data[key] = val

        self.resource = resource_name
        self.api = api

    def __getattr__(self, attr):
        try:
            return self._data[attr]
        except KeyError:
            raise AttributeError(attr)

    def __repr__(self):
        return "%s" % self._data

    def printable_keys(self):
        return sorted([key for key in self._data.keys()
                            if key not in self.__unprintable_keys])

    def printable_items(self):
        return sorted([(key, val) for key, val in self._data.items()
                                    if key not in self.__unprintable_keys],
                                    key=lambda pair: pair[0])

    def _refresh(self):
        blob = self.api.get(self.resource_uri)
        for key, val in blob.items():
            setattr(self, key, val)


class ApiCommandResource(ApiResource):
    def get_status(self):
        # This should be the subset of sane combinations...
        return {
                (True, True, False, False): "Finished",
                (True, True, True, False): "Canceled",
                (True, True, False, True): "Failed",
                (False, True, False, False): "Tasked",
                (False, True, True, False): "Canceling",
                }[(self.complete, self.jobs_created,
                   self.cancelled, self.errored)]

    def _simple_monitor(self, output=sys.stderr):
        # FIXME: HYD-731
        # Probably ought to have a timeout here, although the
        # server seems to have its own timeout logic.
        while not self.complete:
            output.write("\r{0:20}: {1}\n".format(self.message, self.get_status())),
            time.sleep(0.5)
            self._refresh()
        output.write("\r{0:20}: {1}\n".format(self.message, self.get_status()))

    def get_monitor(self):
        return self._simple_monitor
