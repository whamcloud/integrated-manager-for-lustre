from django.conf import settings
import os
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestClientErrorResource(ChromaApiTestCase):

    def _check_log(self, value, log_data):
        """verify data"""

        return value in log_data, "%s not in %s" % (value, log_data)

    def test_can_post_errors(self):
        """Test that POSTing a client error is written to the log client_errors.log"""

        data = {
            "cause": "foo",
            "message": "bar",
            "stack": "The stack",
            "url": "api/foo/bar/baz/",
        }

        user_agent = """Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko)
        Chrome/32.0.1678.0 Safari/537.36"""
        expected_os = "MacOS Macintosh X 10.9.0"
        expected_browser = "Chrome 32.0.1678.0"

        with open(os.path.join(settings.LOG_PATH, 'client_errors.log')) as log:
            # simulate empty log by saving the current end
            # and searching from there below.
            log_initial_size = len(log.read())

        resp = self.api_client.post("/api/client_error/", data=data, HTTP_USER_AGENT=user_agent)

        self.assertHttpCreated(resp)

        with open(os.path.join(settings.LOG_PATH, 'client_errors.log')) as log:
            log_contents_after = log.read()[log_initial_size:]

            self.assertTrue(len(log_contents_after) > 0, "No new log messages.")

            for value in data.values():
                self.assertTrue(*self._check_log(value, log_contents_after))
            self.assertTrue(*self._check_log(user_agent, log_contents_after))
            self.assertTrue(*self._check_log(expected_os, log_contents_after))
            self.assertTrue(*self._check_log(expected_browser, log_contents_after))
