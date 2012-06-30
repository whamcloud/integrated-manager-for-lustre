import mock
from tests.unit.chroma_api.tastypie_test import ResourceTestCase
from tests.unit.chroma_core.helper import JobTestCaseWithHost


class ChromaApiTestCase(JobTestCaseWithHost, ResourceTestCase):
    def __init__(self, *args, **kwargs):
        JobTestCaseWithHost.__init__(self, *args, **kwargs)
        ResourceTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        JobTestCaseWithHost.setUp(self)
        ResourceTestCase.setUp(self)

        from chroma_api.authentication import CsrfAuthentication
        self.old_is_authenticated = CsrfAuthentication.is_authenticated
        CsrfAuthentication.is_authenticated = mock.Mock(return_value = True)
        self.api_client.client.login(username = 'debug', password = 'chr0m4_d3bug')

    def tearDown(self):
            from chroma_api.authentication import CsrfAuthentication
            CsrfAuthentication.is_authenticated = self.old_is_authenticated

            ResourceTestCase.tearDown(self)
            JobTestCaseWithHost.tearDown(self)

    def api_set_state_full(self, uri, state):
        original_object = self.api_get(uri)
        original_object['state'] = state
        response = self.api_client.put(uri, data = original_object)
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        self.assertHttpAccepted(response)

        modified_object = self.api_get(uri)
        self.assertEqual(modified_object['state'], state)

    def api_set_state_partial(self, uri, state):
        response = self.api_client.put(uri, data = {'state': state})
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))

        modified_object = self.api_get(uri)
        self.assertEqual(modified_object['state'], state)

    def api_get(self, uri):
        response = self.api_client.get(uri)
        try:
            self.assertHttpOK(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        return self.deserialize(response)

    def spider_api(self):
        from chroma_api.urls import api
        for name, resource in api._registry.items():
            if 'get' in resource._meta.list_allowed_methods:
                list_uri = resource.get_resource_list_uri()
                response = self.api_client.get(list_uri, data = {'limit': 0})
                self.assertEqual(response.status_code, 200, "%s: %s %s" % (list_uri, response.status_code, self.deserialize(response)))
                if 'get' in resource._meta.detail_allowed_methods:
                    objects = self.deserialize(response)['objects']

                    for o in objects:
                        response = self.api_client.get(o['resource_uri'])
                        self.assertEqual(response.status_code, 200, "%s: %s %s" % (o['resource_uri'], response.status_code, self.deserialize(response)))
