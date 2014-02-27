
import logging
from django.utils.unittest import skipIf

from testconfig import config
from tests.integration.core.chroma_integration_testcase import (
    ChromaIntegrationTestCase)

log = logging.getLogger(__name__)


class TestSshAuth(ChromaIntegrationTestCase):
    """Test that ssh authentication works from the API to the server

    Currently this test will try to run against the shared storage only for
    coverage.  These tests all pass because paramiko/ssh fails over to
    passphraseless auth, which is currently how the test storage nodes are
    set up.  Ticket HYD-1901 addresses extending the test infrastructure to
    support the different ssh auth schemes.

    This test completely skips execution against the simulators.
    HYD-1889 addresses the need for simulator support to test ssh auth.  Once
    this is complete, this test can be implemented against the simulator.

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
        server_config_1 = config['lustre_servers'][0]

        profile = self.get_host_profile(server_config_1['address'])

        body = {
            'server_profile': profile['resource_uri'],
            'address': server_config_1['address']
        }

        if callable(extra_params):
            extra_params = extra_params(server_config_1)

        body.update(extra_params)

        return self.chroma_manager.post('/api/test_host/', body=body)

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_public_private_key(self):
        """Test using .ssh/id_rsa private key to authenticate

        This is how all current ssh authentication works.  This will no
        """

        response = self._post_to_test_host({})

        self.assertTrue(response.json['auth'])

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_root_password(self):
        """Passing a root password with effect a root/pw based auth"""

        response = self._post_to_test_host(lambda server_config: {'root_pw': server_config['root_password']})

        self.assertTrue(response.json['auth'])

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_entered_private_key(self):
        """Test user can submit a private key to authenticate"""

        response = self._post_to_test_host({'private_key': "REPLACE_WITH_PRIVATE_KEY FROM_CONFIG"})

        self.assertTrue(response.json['auth'])

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_entered_private_key_with_passphrase(self):
        """Test user can submit an enc private key and passphrase to auth"""

        response = self._post_to_test_host({'private_key': "REPLACE_WITH_PRIVATE_KEY_FROM_CONFIG",
                                            'private_key_passphrase': "REPLACE_WITH_PRIVATE_KEY "
                                                                      "PASSPHRASE_FROM_CONFIG"})

        self.assertTrue(response.json['auth'])
