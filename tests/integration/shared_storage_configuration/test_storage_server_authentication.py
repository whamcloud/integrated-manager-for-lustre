from testconfig import config
from django.utils.unittest import skipIf

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestStorageServerAuthentication(ChromaIntegrationTestCase):

    SERVER = config["lustre_servers"][0]
    SECURITY_FILE_DIR = "/var/lib/chroma"

    def test_server_authentication(self):

        self.host = self.add_hosts([self.SERVER["address"]])
        self.remote_operations.copy_file(
            self.SERVER["address"],
            "%s/private.pem" % self.SECURITY_FILE_DIR,
            "%s/private.pem.save" % self.SECURITY_FILE_DIR,
        )
        self.remote_operations._ssh_address(
            self.SERVER["address"], 'sed -i "2s/$/XCXXXXCVDS/" %s/private.pem' % self.SECURITY_FILE_DIR
        )

        active_lost_contact_filter = {"active": True, "alert_type": "HostContactAlert"}
        self.wait_until_true(lambda: len(self.get_list("/api/alert/", active_lost_contact_filter)) == 1)

        self.remote_operations.rename_file(
            self.SERVER["address"],
            "%s/private.pem.save" % self.SECURITY_FILE_DIR,
            "%s/private.pem" % self.SECURITY_FILE_DIR,
        )
        self.wait_until_true(lambda: len(self.get_list("/api/alert/", active_lost_contact_filter)) == 0)
