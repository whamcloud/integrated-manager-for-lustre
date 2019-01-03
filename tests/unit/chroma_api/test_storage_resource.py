from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins


class TestStorageResourceResource(ChromaApiTestCase):
    def setUp(self):
        super(TestStorageResourceResource, self).setUp()

        self.manager = load_plugins(["loadable_plugin"])
        self.assertEquals(self.manager.get_errored_plugins(), [])

        import chroma_core

        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager

        # Re-initialize queryset to pick up loaded plugins
        from chroma_api.storage_resource import StorageResourceResource, filter_class_ids
        from chroma_core.models import StorageResourceRecord

        StorageResourceResource._meta.queryset = StorageResourceRecord.objects.filter(
            resource_class__id__in=filter_class_ids()
        )

    def tearDown(self):
        import chroma_core

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager

        super(TestStorageResourceResource, self).tearDown()

    def test_alias_put(self):
        """Check that the 'alias' attribute is validated as non-blank during PUTs"""
        response = self.api_client.post(
            "/api/storage_resource/",
            data={"plugin_name": "loadable_plugin", "class_name": "TestScannableResource", "attrs": {"name": "foobar"}},
        )
        self.assertHttpCreated(response)
        resource = self.deserialize(response)

        valid_alias = "foobar"
        response = self.api_client.put(resource["resource_uri"], data={"alias": valid_alias})
        self.assertHttpOK(response)
        response = self.api_client.get(resource["resource_uri"])
        self.assertEqual(self.deserialize(response)["alias"], valid_alias)

        invalid_aliases = [
            (" ", "May not be blank"),
            ("foo ", "No trailing whitespace allowed"),
            ("", "May not be blank"),
            (" foo", "No trailing whitespace allowed"),
        ]

        for invalid_alias, expected_error in invalid_aliases:
            # Check that an invalid alias gives a validation error
            response = self.api_client.put(resource["resource_uri"], data={"alias": invalid_alias})
            self.assertHttpBadRequest(response)
            errors = self.deserialize(response)
            self.assertIn("alias", errors)
            self.assertEqual(errors["alias"], [expected_error])

            # Check that the alias is still the last valid one we set
            response = self.api_client.get(resource["resource_uri"])
            self.assertEqual(self.deserialize(response)["alias"], valid_alias)
