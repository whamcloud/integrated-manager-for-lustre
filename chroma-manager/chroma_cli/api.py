#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json

from chroma_cli.exceptions import InvalidApiResource, UnsupportedFormat, NotFound, TooManyMatches


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


class ApiClient(object):
    def __init__(self, serializer=None):
        import requests
        self.client = requests.session()
        self.serializer = serializer

        if not self.serializer:
            self.serializer = JsonSerializer()

    def get_content_type(self, short_format):
        return self.serializer.content_types.get(short_format,
                                                 'application/json')

    def get(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        return self.client.get(uri, headers=headers,
                               params=data, auth=authentication)

    def post(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        return self.client.post(uri, headers=headers,
                                data=data, auth=authentication)

    def put(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        return self.client.put(uri, headers=headers,
                               data=data, auth=authentication)

    def delete(self, uri, format="json", data=None, authentication=None, **kwargs):
        content_type = self.get_content_type(format)
        headers = {'Content-Type': content_type, 'Accept': content_type}

        return self.client.delete(uri, headers=headers,
                                  data=data, auth=authentication)


class ApiHandle(object):
    ApiClient = ApiClient

    def __init__(self):
        self.__schema = None
        self.base_url = "http://localhost/api"
        self.authentication = {}
        self.endpoints = ApiEndpointGenerator(self)
        self.api_client = self.ApiClient()
        self.serializer = JsonSerializer()

    @property
    def schema(self):
        if not self.__schema:
            self.__schema = self.send_and_decode("get", "")

        return self.__schema

    def send_and_decode(self, method_name, relative_url, data=None, authentication=None):
        from urlparse import urljoin
        full_url = urljoin(self.base_url, relative_url)
        method = getattr(self.api_client, method_name)
        r = method(full_url, data=data, authentication=authentication)
        return self.serializer.deserialize(r.content)


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
                                          self.name.capitalize())
        except AttributeError:
            # generic fallback
            self.resource_klass = chroma_cli.api_resource.ApiResource

    @property
    def schema(self):
        if not self.__schema:
            schema_url = self.api_handle.schema[self.name]['schema']
            self.__schema = self.api_handle.send_and_decode("get", schema_url)

        return self.__schema

    @property
    def url(self):
        return self.api_handle.schema[self.name]['list_endpoint']

    def resolve_id(self, query):
        try:
            # Slight hack here -- relies on the "name" field usually being
            # first in a reverse-sort in order to optimize for the most
            # common query.
            for field, expressions in (
                    sorted(self.schema['filtering'].iteritems(),
                           key=lambda x: x[0], reverse=True)):
                for expression in expressions:
                    filter = "%s__%s" % (field, expression)

                    candidates = self.list(**{filter: query})
                    if len(candidates) > 1:
                        raise TooManyMatches("The query %s/%s matches more than one resource: %s" % (self.name, query, candidates))

                    try:
                        if query in candidates[0][field]:
                            return candidates[0]['id']
                    except IndexError:
                        continue
        except KeyError:
            # No filtering possible?
            pass

        raise NotFound("Unable to resolve id for %s/%s" % (self.name, query))

    def get_decoded(self, url=None, **data):
        if not url:
            url = self.url
        return self.api_handle.send_and_decode("get", url, data=data)

    def list(self, **data):
        resources = []
        try:
            for object in self.get_decoded(**data)['objects']:
                resources.append(self.resource_klass(**object))
        except ValueError:
            pass
        return resources

    def show(self, subject):
        id = self.resolve_id(subject)
        from urlparse import urljoin
        object = self.get_decoded(url=urljoin(self.url, "%s/" % id))
        return self.resource_klass(**object)
