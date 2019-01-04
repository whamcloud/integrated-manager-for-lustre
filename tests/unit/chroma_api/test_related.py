import mock
from unittest import TestCase

from chroma_api.related_field import dehydrate_related


class TestRelated(TestCase):
    def setUp(self):
        self.mock_related_field = mock.Mock()
        self.mock_related_resource = mock.Mock()
        self.mock_bundle = mock.Mock()
        self.mock_related_bundle = mock.Mock()

        self.mock_related_field.should_full_dehydrate = mock.Mock()
        self.mock_related_resource.build_bundle = mock.Mock(return_value=self.mock_related_bundle)

    def test_related_optional_expanded(self):
        """ Test that an optional expand overrides a default full of false in dehydrate_related """
        self.mock_related_field.should_full_dehydrate.return_value = False
        self.mock_related_field.instance_name = "test_resource"

        self.mock_bundle.request.GET = {"dehydrate__test_resource": True}
        self.mock_related_bundle.request.GET = {"dehydrate__test_resource": True}

        dehydrate_related(self.mock_related_field, self.mock_bundle, self.mock_related_resource)

        self.mock_related_resource.build_bundle.assert_called_once_with(
            obj=self.mock_related_resource.instance,
            request=self.mock_bundle.request,
            objects_saved=self.mock_bundle.objects_saved,
        )
        self.mock_related_resource.full_dehydrate.assert_called_once_with(self.mock_related_bundle)
        self.assertEqual(self.mock_related_resource.get_resource_uri.call_count, 0)
        self.assertEqual(self.mock_related_bundle.request.GET, {"dehydrate__test_resource": True})

    def test_related_default_expanded(self):
        """ Test that an default full of False works in dehydrate_related """
        self.mock_related_field.should_full_dehydrate.return_value = True
        self.mock_related_field.instance_name = "test_resource"

        self.mock_bundle.request.GET = {}
        self.mock_related_bundle.request.GET = {}

        dehydrate_related(self.mock_related_field, self.mock_bundle, self.mock_related_resource)

        self.mock_related_resource.build_bundle.assert_called_once_with(
            obj=self.mock_related_resource.instance,
            request=self.mock_bundle.request,
            objects_saved=self.mock_bundle.objects_saved,
        )
        self.mock_related_resource.full_dehydrate.assert_called_once_with(self.mock_related_bundle)
        self.assertEqual(self.mock_related_resource.get_resource_uri.call_count, 0)
        self.assertEqual(self.mock_related_bundle.request.GET, {})

    def test_related_optional_unexpanded(self):
        """ Test that an optional no expand overrides a default full of true in dehydrate_related """

        self.mock_related_field.should_full_dehydrate.return_value = True
        self.mock_related_field.instance_name = "test_resource"

        for false_ in [False, "false", "False", 0, "0", None]:
            self.mock_related_field.reset_mock()
            self.mock_related_resource.reset_mock()
            self.mock_bundle.reset_mock()

            self.mock_bundle.request.GET = {"dehydrate__test_resource": false_}

            dehydrate_related(self.mock_related_field, self.mock_bundle, self.mock_related_resource)

            self.assertEqual(self.mock_related_resource.build_bundle.call_count, 0)
            self.assertEqual(self.mock_related_resource.full_dehydrate.call_count, 0)
            self.mock_related_resource.get_resource_uri.assert_called_once_with(self.mock_bundle)
            self.assertEqual(self.mock_bundle.request.GET, {"dehydrate__test_resource": false_})

    def test_related_default_unexpanded(self):
        """ Test that an default full of False works in dehydrate_related """

        self.mock_related_field.should_full_dehydrate.return_value = False
        self.mock_related_field.instance_name = "test_resource"

        self.mock_bundle.request.GET = {}

        dehydrate_related(self.mock_related_field, self.mock_bundle, self.mock_related_resource)

        self.assertEqual(self.mock_related_resource.build_bundle.call_count, 0)
        self.assertEqual(self.mock_related_resource.full_dehydrate.call_count, 0)
        self.mock_related_resource.get_resource_uri.assert_called_once_with(self.mock_bundle)
        self.assertEqual(self.mock_bundle.request.GET, {})
