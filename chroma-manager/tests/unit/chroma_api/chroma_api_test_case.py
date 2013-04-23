import mock
from tests.unit.chroma_api.tastypie_test import ResourceTestCase
from tests.unit.chroma_core.helper import synthetic_volume_full


class ChromaApiTestCase(ResourceTestCase):
    """
    Unit tests which drive the *Resource classes in chroma_api/
    """
    def setUp(self):
        super(ChromaApiTestCase, self).setUp()
        from chroma_api.authentication import CsrfAuthentication
        self.old_is_authenticated = CsrfAuthentication.is_authenticated
        CsrfAuthentication.is_authenticated = mock.Mock(return_value = True)
        self.api_client.client.login(username = 'debug', password = 'chr0m4_d3bug')

        # If the test that just ran imported storage_plugin_manager, it will
        # have instantiated its singleton, and created some DB records.
        # Django TestCase rolls back the database, so make sure that we
        # also roll back (reset) this singleton.
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = chroma_core.lib.storage_plugin.manager.StoragePluginManager()

    def tearDown(self):
        from chroma_api.authentication import CsrfAuthentication
        CsrfAuthentication.is_authenticated = self.old_is_authenticated

    def api_set_state_full(self, uri, state):
        original_object = self.api_get(uri)
        original_object['state'] = state
        response = self.api_client.put(uri, data = original_object)
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        self.assertHttpAccepted(response)

    def api_set_state_partial(self, uri, state):
        response = self.api_client.put(uri, data = {'state': state})
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))

    def api_get(self, uri):
        response = self.api_client.get(uri)
        try:
            self.assertHttpOK(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        return self.deserialize(response)

    def create_simple_filesystem(self, host):
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(host).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt, _ = ManagedMdt.create_for_volume(synthetic_volume_full(host).id, filesystem = self.fs)
        self.ost, _ = ManagedOst.create_for_volume(synthetic_volume_full(host).id, filesystem = self.fs)

    def api_get_list(self, uri):
        response = self.api_client.get(uri)
        try:
            self.assertHttpOK(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))
        return self.deserialize(response)['objects']

    def api_patch_attributes(self, uri, attributes):
        response = self.api_client.patch(uri, data = attributes)
        try:
            self.assertHttpAccepted(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))

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
