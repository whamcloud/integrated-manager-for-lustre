# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import namedtuple
import mock

from tastypie import http
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase

from chroma_api.utils import BulkResourceOperation

FakeBundle = namedtuple("FakeBundle", ["data"])


class TestException(Exception):
    def __init__(self, response_klass, response_data):
        self.response_klass = response_klass
        self.response_data = response_data


def mock_custom_response(resource, request, response_klass, response_data):
    return TestException(response_klass, response_data)


class TestBulkResourceOperation(ChromaApiTestCase, BulkResourceOperation):
    def setUp(self):
        super(TestBulkResourceOperation, self).setUp()

        self.object_count = 10
        self.fail_object_index = self.object_count / 2

    @mock.patch("chroma_api.utils.custom_response", new=mock_custom_response)
    def test_bulk_passing_case(self):
        def _passing_action(self, data, request, **kwargs):
            return self.BulkActionResult(data["data"], None, None)

        try:
            self._bulk_operation(
                _passing_action,
                "passing",
                FakeBundle({"objects": [{"data": n} for n in range(0, self.object_count)]}),
                None,
            )
        except TestException as e:
            self.assertEqual(e.response_klass, http.HttpAccepted)
            self.assertEqual(len(e.response_data["objects"]), self.object_count)

            for index, object in enumerate(e.response_data["objects"]):
                self.assertEqual(object["passing"], index)
                self.assertEqual(object["error"], None)
                self.assertEqual(object["traceback"], None)

    @mock.patch("chroma_api.utils.custom_response", new=mock_custom_response)
    def test_bulk_failing_case(self):
        def _failing_action(self, data, request, **kwargs):
            if data["data"] != self.fail_object_index:
                return self.BulkActionResult(data["data"], None, None)
            else:
                return self.BulkActionResult(None, "Error String", "Traceback String")

        try:
            self._bulk_operation(
                _failing_action,
                "failing",
                FakeBundle({"objects": [{"data": n} for n in range(0, self.object_count)]}),
                None,
            )
        except TestException as e:
            self.assertEqual(e.response_klass, http.HttpBadRequest)
            self.assertEqual(len(e.response_data["objects"]), self.object_count)

            for index, object in enumerate(e.response_data["objects"]):
                if index == self.fail_object_index:
                    self.assertEqual(object["failing"], None)
                    self.assertEqual(object["error"], "Error String")
                    self.assertEqual(object["traceback"], "Traceback String")
                else:
                    self.assertEqual(object["failing"], index)
                    self.assertEqual(object["error"], None)
                    self.assertEqual(object["traceback"], None)

    @mock.patch("chroma_api.utils.custom_response", new=mock_custom_response)
    def test_single_passing_case(self):
        def _passing_action(self, data, request, **kwargs):
            return self.BulkActionResult(data["data"], None, None)

        try:
            self._bulk_operation(_passing_action, "passing", FakeBundle({"data": 123}), None)
        except TestException as e:
            self.assertEqual(e.response_klass, http.HttpAccepted)
            self.assertEqual(e.response_data, 123)

    @mock.patch("chroma_api.utils.custom_response", new=mock_custom_response)
    def test_single_failing_case(self):
        def _failing_action(self, data, request, **kwargs):
            return self.BulkActionResult(None, "Error String", "Traceback String")

        try:
            self._bulk_operation(_failing_action, "failing", FakeBundle({"data": 123}), None)
        except TestException as e:
            self.assertEqual(e.response_klass, http.HttpBadRequest)
            self.assertEqual(e.response_data["error"], "Error String")
            self.assertEqual(e.response_data["traceback"], "Traceback String")

    @mock.patch("chroma_api.utils.custom_response", new=mock_custom_response)
    def test_single_failing_exception_case(self):
        def _failing_action(self, data, request, **kwargs):
            raise Exception("An exception occurred")

        try:
            self._bulk_operation(_failing_action, "failing", FakeBundle({"data": 123}), None)
        except TestException as e:
            self.assertEqual(e.response_klass, http.HttpBadRequest)
            self.assertEqual(e.response_data["error"], "An exception occurred")
            self.assertTrue("most recent call last" in e.response_data["traceback"])
