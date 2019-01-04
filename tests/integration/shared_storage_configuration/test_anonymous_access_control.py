from testconfig import config
from django.utils.unittest import skip

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestAnonymousAccessControl(ChromaIntegrationTestCase):

    manager = config["chroma_managers"][0]
    SETTINGS_DIR = "/usr/share/chroma-manager"

    def _check_access(self, chroma_manager, expect_success):
        # Some end points just can't be fetched so we have to ignore them.
        end_points_to_ignore = [
            "/api/help/",
            "/api/test_host/",
            "/api/system_status/",
            "/api/updates_available/",
            "/api/session/",
        ]

        end_points = self.get_json_by_uri("/api/", args={"limit": 0})

        for end_point in end_points.values():
            if end_point["list_endpoint"] not in end_points_to_ignore:
                response = chroma_manager.get(end_point["list_endpoint"], params={"limit": 0})
                self.assertEqual(response.successful, expect_success)

    def _write_local_settings_file(self):
        file_content = "ALLOW_ANONYMOUS_READ = False"
        self.remote_operations.create_file(
            self.manager["fqdn"], file_content, "%s/local_settings.py" % self.SETTINGS_DIR
        )

    def test_access_control(self):

        try:
            self._check_access(self.chroma_manager, True)
            self._check_access(self.unauthorized_chroma_manager, True)

            self._write_local_settings_file()
            self.restart_chroma_manager(self.manager["fqdn"])

            self._check_access(self.chroma_manager, True)
            self._check_access(self.unauthorized_chroma_manager, False)
        finally:
            self.remote_operations.delete_file(self.manager["fqdn"], "%s/local_settings.py*" % self.SETTINGS_DIR)
            self.restart_chroma_manager(self.manager["fqdn"])
