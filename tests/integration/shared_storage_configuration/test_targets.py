from testconfig import config
from django.utils.unittest.case import skipIf
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestTargets(ChromaIntegrationTestCase):
    """Exercise target operations done via the /api/target/
    (this is a separate path to the typical filesystem ops done via /api/filesystem/)"""

    def test_create_mgt(self):
        self.add_hosts([config["lustre_servers"][0]["address"]])
        volumes = self.get_usable_volumes()

        response = self.chroma_manager.post("/api/target/", body={"volume_id": volumes[0]["id"], "kind": "MGT"})

        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json["target"]["resource_uri"]
        create_command = response.json["command"]["id"]
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, "mounted")

        self.set_state(target_uri, "unmounted")
        self.set_state(target_uri, "mounted")

        response = self.chroma_manager.delete(target_uri)
        self.assertEqual(response.status_code, 202)
        delete_command = response.json["command"]
        self.wait_for_command(self.chroma_manager, delete_command["id"])

    def test_create_ost(self):
        filesystem_id = self.create_filesystem_standard(self.TEST_SERVERS)
        filesystem_uri = "/api/filesystem/%s/" % filesystem_id

        volume = self.get_usable_volumes()[0]
        response = self.chroma_manager.post(
            "/api/target/", body={"volume_id": volume["id"], "kind": "OST", "filesystem_id": filesystem_id}
        )
        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json["target"]["resource_uri"]
        create_command = response.json["command"]["id"]
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, "mounted")
        self.assertState(filesystem_uri, "available")

        self.set_state(target_uri, "unmounted")
        self.assertState(filesystem_uri, "unavailable")
        self.set_state(target_uri, "mounted")
        self.assertState(filesystem_uri, "available")

        response = self.chroma_manager.delete(target_uri)
        self.assertEqual(response.status_code, 202)
        delete_command = response.json["command"]
        self.wait_for_command(self.chroma_manager, delete_command["id"])


class TestReformatTarget(ChromaIntegrationTestCase):
    """
    Exercise the code that copes with attempts to format a volume that already
    contains a filesystem.
    """

    def _format(self, occupy_initial=False, occupy_after_add=False, reformat=False):
        """
        :param occupy_initial: Create a local filesystem on the volume before adding the server to chroma.
        :param occupy_after_add: Create a local filesystem on the volume after adding the server to chroma.
        :param reformat: argument to target creation POST
        """
        # Pick one victim volume ahead of running tests
        device_index = next(
            device["path_index"] for device in config["lustre_devices"] if device["backend_filesystem"] == "ldiskfs"
        )
        host_config = config["lustre_servers"][0]
        device_path = host_config["device_paths"][device_index]

        # Optionally create a local filesystem on a volume before it is added to chroma
        if occupy_initial:
            self.remote_operations.format_block_device(host_config["fqdn"], device_path, "ext2")

        # Now add it to chroma
        self.add_hosts([host_config["address"]])
        volumes = self.get_usable_volumes()

        if occupy_initial:
            self.remote_operations.format_block_device(host_config["fqdn"], device_path, "ext2")

        # Check that our victim volume has come back over the API and is marked as occupied
        # NB logic here relies on there only being one server in play
        victim_volume = None
        for v in volumes:
            if v["volume_nodes"][0]["path"] == device_path:
                victim_volume = v
                break
        self.assertIsNotNone(victim_volume)
        if occupy_initial:
            self.assertEqual(victim_volume["filesystem_type"], "ext2")
        else:
            self.assertEqual(victim_volume["filesystem_type"], None)

        # Optionally create a local filesystem on a volume that has already been detected by
        # chroma
        if occupy_after_add:
            self.remote_operations.format_block_device(host_config["fqdn"], device_path, "ext2")

        response = self.chroma_manager.post(
            "/api/target/", body={"volume_id": victim_volume["id"], "kind": "MGT", "reformat": reformat}
        )
        self.assertEqual(response.status_code, 202, response.text)
        return response.json["command"]["id"]

    def _get_failed_step(self, command):
        # The command should fail in its PreFormatCheck
        self.assertTrue(command["errored"])
        failed_job = None
        for job_uri in command["jobs"]:
            job = self.get_json_by_uri(job_uri)
            if job["errored"]:
                failed_job = job
                break
        self.assertIsNotNone(failed_job)

        failed_step = None
        for step_uri in failed_job["steps"]:
            step = self.get_json_by_uri(step_uri)
            if step["state"] == "failed":
                failed_step = step
                break
        self.assertIsNotNone(failed_step)
        return failed_step

    @skipIf(ChromaIntegrationTestCase.linux_devices_exist() is False, "test requires a linux device, none found")
    def test_format_occupied_device(self):
        """
        Test that attempting to format a block device which
        contains a filesystem is prevented from erasing
        the device.

        This is the easy case, the device is known to be formatted
        before chroma adds the host.

        The format operation should be prevented.
        """
        command_id = self._format(occupy_initial=True)
        command = self.wait_for_command(self.chroma_manager, command_id, verify_successful=False)
        failed_step = self._get_failed_step(command)
        self.assertEqual(failed_step["class_name"], "PreFormatCheck")

    @skipIf(ChromaIntegrationTestCase.linux_devices_exist() is False, "test requires a linux device, none found")
    def test_reformat_occupied_device(self):
        """
        Test that if a block device contains a filesystem, we
        can use it for Lustre by explicitly asking for it to be reformatted

        The format operation should succeed.
        """

        command_id = self._format(occupy_initial=True, reformat=True)
        self.wait_for_command(self.chroma_manager, command_id, verify_successful=True)

    @skipIf(ChromaIntegrationTestCase.linux_devices_exist() is False, "test requires a linux device, none found")
    def test_format_live_occupied_device(self):
        """
        Like test_format_occupied_device, but the device
        is initially empty, then we insert a filesystem
        just before asking chroma to format it.  Check that
        chroma can catch this at the last minute.

        The format operation should be prevented.
        """

        command_id = self._format(occupy_after_add=True)
        command = self.wait_for_command(self.chroma_manager, command_id, verify_successful=False)
        failed_step = self._get_failed_step(command)
        self.assertEqual(failed_step["class_name"], "PreFormatCheck")

    @skipIf(ChromaIntegrationTestCase.linux_devices_exist() is False, "test requires a linux device, none found")
    def test_reformat_live_occupied_device(self):
        """
        Test that reformatting works even if we only find out the volume is occupied
        after the initial host add.

        The format operation should succeed.
        """

        command_id = self._format(occupy_after_add=True, reformat=True)
        self.wait_for_command(self.chroma_manager, command_id, verify_successful=True)
