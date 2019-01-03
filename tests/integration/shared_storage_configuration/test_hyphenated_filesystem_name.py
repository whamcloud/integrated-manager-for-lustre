from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestHyphenatedFilesystemName(ChromaIntegrationTestCase):
    def test_hyphenated_named_filesystem(self):
        filesystem_id = self.create_filesystem_standard(config["lustre_servers"][0:4], name="test-fs")

        self.assertState("/api/filesystem/%s/" % filesystem_id, "available")
        filesystem = self.get_filesystem(filesystem_id)

        self.set_state(filesystem["resource_uri"], "stopped")
        self.set_state(filesystem["resource_uri"], "available")

        client = config["lustre_clients"][0]["address"]
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_operations.exercise_filesystem(client, filesystem)
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)
