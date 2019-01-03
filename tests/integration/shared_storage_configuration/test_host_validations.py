from testconfig import config
from django.utils.unittest import skipIf
from iml_common.lib.name_value_list import NameValueList
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestHostValidations(ChromaIntegrationTestCase):
    def setUp(self):
        super(ChromaIntegrationTestCase, self).setUp()
        self.manager = config["chroma_managers"][0]
        self.server = config["lustre_servers"][0]

        # We want to stop the ssh's being validated by the local private key so move it out of the way.
        self.remote_operations.rename_file(self.manager["address"], "~/.ssh/id_rsa", "~/.ssh/id_rsa.deleted")

        self.id_rsa = self.remote_operations.read_file(self.manager["address"], "~/.ssh/id_rsa.deleted")

    def tearDown(self):
        self.remote_operations.rename_file(self.manager["address"], "~/.ssh/id_rsa.deleted", "~/.ssh/id_rsa")

    def _post_test_host(self, **body):
        response = self.chroma_manager.post("/api/test_host/", body=body)

        self.wait_for_command(self.chroma_manager, response.json["id"])

        response = self.chroma_manager.get(response.json["jobs"][0])
        self.assertTrue(response.successful, response.text)
        validations = response.json["step_results"].values()[0]

        return NameValueList(validations["status"])

    def test_add_non_existent_host_fails_to_resolve(self):
        validation_values = self._post_test_host(
            address="foo.mycompany.notwhamcloud.com", auth_type="existing_keys_choice"
        )

        self.assertFalse(validation_values["resolve"])

    def test_add_host_private_key_authentication_check(self):
        for private_key in ["notakey", self.id_rsa]:
            validation_values = self._post_test_host(
                address=self.server["address"], auth_type="private_key_choice", private_key=private_key
            )

            self.assertTrue(validation_values["resolve"])
            self.assertEqual(validation_values["auth"], private_key == self.id_rsa)

    def test_add_host_root_password_authentication_check(self):
        root_password = self.server["root_password"]
        modded_password = "dragonballz" + root_password

        for password in [modded_password, root_password]:
            validation_values = self._post_test_host(
                address=self.server["address"], auth_type="id_password_root", root_password=password
            )

            self.assertTrue(validation_values["resolve"])
            self.assertEqual(validation_values["auth"], password == root_password)
