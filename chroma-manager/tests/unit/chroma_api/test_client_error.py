from chroma_core.models.client_error import ClientError
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestClientErrorResource(ChromaApiTestCase):
    def test_can_post_errors(self):
        data = {
            "cause": "foo",
            "message": "bar",
            "stack": "The stack",
            "url": "api/foo/bar/baz/",
            "user_agent": "meh"
        }

        user_agent = """Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko)
        Chrome/32.0.1678.0 Safari/537.36"""

        resp = self.api_client.post("/api/client_error/", data=data, HTTP_USER_AGENT=user_agent)

        self.assertHttpCreated(resp)

        self.assertEquals(ClientError.objects.count(), 1)

        client_error_record = ClientError.objects.get(message="bar")

        self.assertEqual(client_error_record.cause, data["cause"])
        self.assertEqual(client_error_record.message, data["message"])
        self.assertEqual(client_error_record.stack, data["stack"])
        self.assertEqual(client_error_record.url, data["url"])
        self.assertEqual(client_error_record.os, "MacOS Macintosh X 10.9.0")
        self.assertEqual(client_error_record.browser, "Chrome 32.0.1678.0")
        self.assertEqual(client_error_record.user_agent, user_agent)
