from testconfig import config
from django.utils.unittest import skipIf
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestHostid(ChromaIntegrationTestCase):
    def test_create_hostid(self):
        """
        Test that when a host is added, the /etc/hostid file is created containing a 'unique' binary identity.

        This identity is used by Lustre when providing Multi-Mount Protection (SPL) during failover of ZFS-backed targets.

        Reference HYD-5037 and LU-7134
        """
        hostid_path = "/etc/hostid"
        address = self.TEST_SERVERS[0]["address"]

        self.remote_operations._ssh_address(address, "rm -rf %s" % hostid_path, expected_return_code=None)

        # Verify hostid is not present before host is set up
        self.assertFalse(self.remote_operations.file_exists(address, hostid_path))

        # Add one host
        self.add_hosts([address])

        # Ensure hostid file has been created and is not empty
        self.assertTrue(self.remote_operations.file_exists(address, hostid_path))
