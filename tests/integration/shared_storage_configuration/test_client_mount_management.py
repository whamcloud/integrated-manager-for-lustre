from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestClientMountManagement(ChromaIntegrationTestCase):
    def _get_mount_job(self, job_class):
        self.worker = self.get_json_by_uri(self.worker["resource_uri"])

        for action in self.worker["available_actions"]:
            if action.get("class_name", None) == job_class:
                return action

        return None

    def setUp(self):
        self.TEST_SERVERS.append(self.config_workers[0])
        super(TestClientMountManagement, self).setUp()

        filesystem_id = self.create_filesystem_standard(self.TEST_SERVERS)
        self.filesystem = self.get_json_by_uri("/api/filesystem/%s" % filesystem_id)
        self.worker = self.add_hosts([self.config_workers[0]["address"]])[0]

    def test_mount_and_unmount(self):
        # Technically, these should probably be split up. Implementing
        # that correctly is nontrivial.
        mount_job_name = "MountLustreFilesystemsJob"
        unmount_job_name = "UnmountLustreFilesystemsJob"

        mount = self.create_client_mount(self.worker["resource_uri"], self.filesystem["resource_uri"], "/mnt/testfs")

        # Make sure we're starting unmounted
        self.assertEqual(mount["state"], "unmounted")

        # Mount the client
        self.wait_until_true(lambda: self._get_mount_job(mount_job_name))
        mount_job = self._get_mount_job(mount_job_name)
        command = self.chroma_manager.post(
            "/api/command/",
            body=dict(jobs=[mount_job], message="Test %s (%s)" % (mount_job_name, self.worker["address"])),
        ).json
        self.wait_for_command(self.chroma_manager, command["id"])
        self.wait_for_assert(lambda: self.assertEqual(self.get_json_by_uri(mount["resource_uri"])["state"], "mounted"))

        # Now unmount it
        self.wait_until_true(lambda: self._get_mount_job(unmount_job_name))
        unmount_job = self._get_mount_job(unmount_job_name)
        command = self.chroma_manager.post(
            "/api/command/",
            body=dict(jobs=[unmount_job], message="Test %s (%s)" % (mount_job_name, self.worker["address"])),
        ).json
        self.wait_for_command(self.chroma_manager, command["id"])
        self.wait_for_assert(
            lambda: self.assertEqual(self.get_json_by_uri(mount["resource_uri"])["state"], "unmounted")
        )
