
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

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_public_private_key(self):
        """Test using .ssh/id_rsa private key to authenticate

        This is how all current ssh authentication works.  This will no
        """

        server_config_1 = config['lustre_servers'][0]

        response = self.chroma_manager.post(
            '/api/test_host/',
            body = {'address': server_config_1['address']}
        )

        self.assertTrue(response.json['auth'])

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_root_password(self):
        """Passing a root password with effect a root/pw based auth"""

        server_config_1 = config['lustre_servers'][0]

        response = self.chroma_manager.post(
            '/api/test_host/',
            body = {'address': server_config_1['address'],
                    'root_pw': server_config_1['root_password']}
        )

        self.assertTrue(response.json['auth'])

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_entered_private_key(self):
        """Test user can submit a private key to authenticate"""

        server_config_1 = config['lustre_servers'][0]

        response = self.chroma_manager.post(
            '/api/test_host/',
            body = {'address': server_config_1['address'],
                    'private_key': "REPLACE_WITH_PRIVATE_KEY"
                                   "FROM_CONFIG"}
        )

        self.assertTrue(response.json['auth'])

    @skipIf(config.get('simulator'), "Requires HYD-1889")
    def test_entered_private_key_with_passphrase(self):
        """Test user can submit an enc private key and passphrase to auth"""

        server_config_1 = config['lustre_servers'][0]

        response = self.chroma_manager.post(
            '/api/test_host/',
            body = {'address': server_config_1['address'],
                    'private_key': "REPLACE_WITH_PRIVATE_KEY_FROM_CONFIG",
                    'private_key_passphrase': "REPLACE_WITH_PRIVATE_KEY "
                                              "PASSPHRASE_FROM_CONFIG"}
        )

        self.assertTrue(response.json['auth'])
