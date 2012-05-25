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

    def spider_api(self):
        from chroma_api.urls import api
        for name, resource in api._registry.items():
            if 'get' in resource._meta.list_allowed_methods:
                response = self.api_client.get(resource.get_resource_list_uri())
                self.assertHttpOK(response)
                if 'get' in resource._meta.detail_allowed_methods:
                    objects = self.deserialize(response)['objects']

                    for o in objects:
                        self.api_client.get(o['resource_uri'])
                        self.assertHttpOK(response)
