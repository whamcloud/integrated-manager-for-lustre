from collections import defaultdict

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase

from chroma_api.validation_utils import ChromaValidation


class MockResource(object):
    # This gives up MockResource.Meta.object_class.DoesNotExist
    class MockClass(object):
        object_class = None
        DoesNotExist = Exception

    Meta = MockClass
    Meta.object_class = Meta

    @classmethod
    def get_via_uri(cls, uri, request=None):
        if uri == "valid":
            return uri
        else:
            raise cls.Meta.object_class.DoesNotExist


class ChromaValidationTestCase(ChromaApiTestCase):
    def test_items_present(self):
        validation = ChromaValidation()

        errors = defaultdict(list)

        self.assertFalse(
            validation.validate_object(
                {"field1": 1, "field2": 2},
                errors,
                {"field1": ChromaValidation.Expectation(True), "field2": ChromaValidation.Expectation(True)},
            )
        )

        self.assertEqual(errors, {})

    def test_items_missing(self):
        validation = ChromaValidation()

        errors = defaultdict(list)

        self.assertTrue(
            validation.validate_object(
                {"field1": 1},
                errors,
                {"field1": ChromaValidation.Expectation(True), "field2": ChromaValidation.Expectation(True)},
            )
        )

        self.assertEqual(errors, {"field2": ["Field field2 not present in data"]})

    def test_items_missing_optional(self):
        validation = ChromaValidation()

        errors = defaultdict(list)

        self.assertFalse(
            validation.validate_object(
                {"field1": 1},
                errors,
                {"field1": ChromaValidation.Expectation(True), "field2": ChromaValidation.Expectation(False)},
            )
        )

        self.assertEqual(errors, {})

    def test_items_extra(self):
        validation = ChromaValidation()

        errors = defaultdict(list)

        self.assertTrue(
            validation.validate_object(
                {"field1": 1, "field2": 2, "field3": 3},
                errors,
                {"field1": ChromaValidation.Expectation(True), "field2": ChromaValidation.Expectation(True)},
            )
        )

        self.assertEqual(errors, {"field3": ["Additional field(s) field3 found in data"]})

    def test_uri_valid(self):
        validation = ChromaValidation()

        errors = defaultdict(list)

        self.assertFalse(validation.validate_resources([validation.URIInfo("valid", MockResource)], errors))

        self.assertEqual(errors, {})

    def test_uri_invalid(self):
        validation = ChromaValidation()

        errors = defaultdict(list)

        self.assertTrue(validation.validate_resources([validation.URIInfo("invalid", MockResource)], errors))

        self.assertEqual(errors, {"invalid": ["Resource invalid was not found"]})
