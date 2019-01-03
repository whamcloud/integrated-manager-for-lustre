import logging
from django.utils.unittest import skipIf

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from iml_common.lib.name_value_list import NameValueList

log = logging.getLogger(__name__)


class TestSshAuth(ChromaIntegrationTestCase):
    """Test that ssh authentication works from the API to the server

    Currently this test will try to run against the shared storage only for
    coverage.  These tests all pass because paramiko/ssh fails over to
    passphraseless auth, which is currently how the test storage nodes are
    set up.  Ticket HYD-1901 addresses extending the test infrastructure to
    support the different ssh auth schemes.

    TODO:  HYD-1902 update this test to use different auth schemes
    """

    def _post_to_test_host(self, extra_params):
        """
        This is a helper function that calls /api/test_host.
        Extra params to post can be provided.
        @type extra_params: dict | (dict) -> dict
        @param extra_params: If a dict, updates the body directly.
          If a lambda is given a server config and returns dict based on lookup in that config.
        @rtype: tests.utils.http_requests.HttpResponse
        @return: A HttpResponse.
        """
        server_config_1 = config["lustre_servers"][0]

        body = {"address": server_config_1["address"]}

        if callable(extra_params):
            extra_params = extra_params(server_config_1)

        body.update(extra_params)

        response = self.chroma_manager.post("/api/test_host/", body=body)

        self.assertEqual(response.successful, True, response.text)
        command_id = response.json["id"]

        self.wait_for_command(self.chroma_manager, command_id, timeout=1200)

        results = []

        for job in response.json["jobs"]:
            response = self.chroma_manager.get(job)
            self.assertEqual(response.successful, True, response.text)

            for item in response.json["step_results"].items():
                results.append(NameValueList(item[1]["status"]))

        # We have a result for each host, but as we have posted 1 host then 1 result
        self.assertEqual(len(results), 1)

        # As we have 1 result just return that result
        return results[0]

    def test_public_private_key(self):
        """Test using .ssh/id_rsa private key to authenticate

        This is how all current ssh authentication works.  This will no
        """

        result = self._post_to_test_host({})

        self.assertTrue(result["auth"])

    def test_root_password(self):
        """Passing a root password with effect a root/pw based auth"""

        result = self._post_to_test_host(lambda server_config: {"root_pw": server_config["root_password"]})

        self.assertTrue(result["auth"])

    def test_entered_private_key(self):
        """Test user can submit a private key to authenticate"""

        result = self._post_to_test_host({"private_key": "REPLACE_WITH_PRIVATE_KEY FROM_CONFIG"})

        self.assertTrue(result["auth"])

    def test_entered_private_key_with_passphrase(self):
        """Test user can submit an enc private key and passphrase to auth"""

        result = self._post_to_test_host(
            {
                "private_key": "REPLACE_WITH_PRIVATE_KEY_FROM_CONFIG",
                "private_key_passphrase": "REPLACE_WITH_PRIVATE_KEY " "PASSPHRASE_FROM_CONFIG",
            }
        )

        self.assertTrue(result["auth"])
