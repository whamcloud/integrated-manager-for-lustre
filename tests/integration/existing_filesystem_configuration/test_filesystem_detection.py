import re

from testconfig import config
from tests.integration.core.stats_testcase_mixin import StatsTestCaseMixin
from tests.integration.core.constants import LONG_TEST_TIMEOUT


class TestFilesystemDetection(StatsTestCaseMixin):
    def setUp(self):
        super(TestFilesystemDetection, self).setUp()

        # Ensure the clients are unmounted.
        self.remote_operations.unmount_clients()

    def _detect_filesystem(self):
        if self.get_list("/api/target/") == []:
            # Attempt to ensure all the targets are mounted for the filesystem.
            for host in config["lustre_servers"]:
                self.remote_command(host["address"], "mount -a -t lustre", expected_return_code=None)

            self.add_hosts([l["address"] for l in config["lustre_servers"]])

            # Verify hosts are immutable
            response = self.chroma_manager.get("/api/host/")
            self.assertEqual(response.successful, True, response.text)
            hosts = response.json["objects"]
            self.assertEqual(len(config["lustre_servers"]), len(hosts))
            for host in hosts:
                self.assertTrue(host["immutable_state"], host)
                available_job_classes = [j["class_name"] for j in host["available_jobs"]]
                self.assertIn("ForceRemoveHostJob", available_job_classes)
                available_transition_states = [t["state"] for t in host["available_transitions"]]
                self.assertListEqual(["removed"], available_transition_states)

            # Issue command to detect existing filesystem
            response = self.chroma_manager.post(
                "/api/command/",
                body={"message": "Detecting filesystems", "jobs": [{"class_name": "DetectTargetsJob", "args": {}}]},
            )
            self.assertEqual(response.successful, True, response.text)
            command = response.json

            self.wait_for_command(self.chroma_manager, command["id"], timeout=LONG_TEST_TIMEOUT)

            # Verify it detected the filesystem
            filesystem = self._filesystem
            self.assertEqual(config["filesystem"]["name"], filesystem["name"])
            self.assertTrue(filesystem["immutable_state"])
            available_states = [t["state"] for t in filesystem["available_transitions"]]
            self.assertIn("forgotten", available_states)
            self.assertNotIn("removed", available_states)

            # Wait for active_host_name to get set on all of the targets
            self.wait_until_true(
                lambda: (
                    len([t for t in self.get_list("/api/target/") if not t["active_host"] is None])
                    == len(config["filesystem"]["targets"])
                )
            )

    def _forget_filesystem(self):
        filesystem = self._filesystem

        self.set_state(
            filesystem["resource_uri"],
            "forgotten",
            verify_successful=False,
            msg="Forgetting Filesystem %s" % filesystem["label"],
        )
        self.assertEqual(len(self.get_list("/api/filesystem/")), 0)
        self.assertEqual(len(self.get_list("/api/target/")), 1)

        self.set_state(
            filesystem["mgt"]["resource_uri"],
            "forgotten",
            verify_successful=False,
            msg="Forgetting MGT %s" % filesystem["mgt"]["label"],
        )
        self.assertEqual(len(self.get_list("/api/target/")), 0)

    @property
    def _filesystem(self):
        # Verify filesystem is available
        response = self.chroma_manager.get("/api/filesystem/", params={"limit": 0})
        self.assertEqual(response.successful, True, response.text)
        self.assertEqual(len(response.json["objects"]), 1)

        return response.json["objects"][0]

    def test_filesystem_detection_verify_attributes(self):
        self._detect_filesystem()

        # Verify target attributes
        targets = self.get_list("/api/target/")

        for target in targets:
            target_config = config["filesystem"]["targets"][target["name"]]

            target_has_secondary = target_config.get("secondary_server") != None
            failover_is_failnode = target_config.get("failover_mode", "failnode") == "failnode"
            mounted_on_secondary = target_config.get("mount_server") == "secondary_server"

            # Allow for special HYD-3807 case
            is_HYD3807 = target_has_secondary and failover_is_failnode and mounted_on_secondary

            # If service node used then the primary is the mounted server, or if is HYD-3807 we will only have found the mounted server
            if is_HYD3807 or (target_config.get("failover_mode") == "servicenode"):
                target_host_config = self.get_host_config(
                    target_config[target_config.get("mount_server", "primary_server")]
                )
            else:
                target_host_config = self.get_host_config(target_config["primary_server"])

            self.assertEqual(target_config["kind"], target["kind"])
            self.assertEqual(target_host_config["fqdn"], target["primary_server_name"])
            self.assertEqual(target_host_config["fqdn"], target["active_host_name"])
            self.assertTrue(target["immutable_state"])
            self.assertEqual("mounted", target["state"])

            if (not is_HYD3807) and target_has_secondary:
                # If service node used then the secondary is the not mounted server
                if target_config.get("failover_mode") == "servicenode":
                    if target_config.get("mount_server") == "secondary_server":
                        target_host_config = self.get_host_config(target_config["primary_server"])
                    else:
                        target_host_config = self.get_host_config(target_config["secondary_server"])
                else:
                    target_host_config = self.get_host_config(target_config["secondary_server"])

                self.assertEqual(target_host_config["fqdn"], target["failover_server_name"])

        # Verify filesystem is available
        filesystem = self._filesystem
        self.assertEqual("available", filesystem["state"])

        # Forget the filesystem and forget the MGT
        self._forget_filesystem()

    def test_filesystem_detection_verify_stats(self):
        self._detect_filesystem()

        filesystem = self._filesystem

        client = config["lustre_clients"][0]["address"]
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_command(
                client,
                "rm -rf /mnt/%s/*" % filesystem["name"],
                expected_return_code=None,  # may not exist - don't care, move along.
            )
            self.remote_operations.exercise_filesystem(client, filesystem)
            self.check_stats(filesystem["id"])
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

        # Forget the filesystem and forget the MGT
        self._forget_filesystem()

    def test_filesystem_detection_verify_mountable(self):
        self._detect_filesystem()

        filesystem = self._filesystem

        # Verify target attributes
        targets = self.get_list("/api/target/")

        # Verify a client can use the filesystem using the mount command provided
        client = config["lustre_clients"][0]["address"]
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_command(
                client,
                "rm -rf /mnt/%s/*" % filesystem["name"],
                expected_return_code=None,  # may not exist - dont care, move along.
            )
            self.remote_operations.exercise_filesystem(client, filesystem)
            self.check_stats(filesystem["id"])
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

        # Verify detects target unmount.
        for target in targets:
            target_config = config["filesystem"]["targets"][target["name"]]
            target_host_config = self.get_host_config(
                target_config[target_config.get("mount_server", "primary_server")]
            )
            result = self.remote_command(target_host_config["address"], "mount")
            if re.search("on %s type lustre" % target_config["mount_path"], result.stdout):
                self.remote_command(target_host_config["address"], "umount %s" % target_config["mount_path"])
                result = self.remote_command(target_host_config["address"], "mount")
                self.assertNotRegexpMatches(result.stdout, "on %s type lustre" % target_config["mount_path"])

        # Verify all targets detected as unmounted
        self.wait_until_true(lambda: self.targets_in_state("unmounted"))

        # Verify filesystem is unavailable
        response = self.chroma_manager.get("/api/filesystem/", params={"limit": 0})
        self.assertEqual(response.successful, True, response.text)
        filesystems = response.json["objects"]
        self.assertEqual(len(filesystems), 1)
        filesystem = filesystems[0]
        self.assertEqual("stopped", filesystem["state"])

        # Remount all targets
        for host in config["lustre_servers"]:
            self.remote_command(host["address"], "mount -a -t lustre")

        # Verify all targets detected as mounted
        self.wait_until_true(lambda: self.targets_in_state("mounted"))

        # Forget the filesystem and forget the MGT
        self._forget_filesystem()

    def test_lnet_up(self):
        """
        Test lnet is reported as up on the test filesystem
        """
        lnet_configurations = self.chroma_manager.get("/api/lnet_configuration/", params={"limit": 0}).json["objects"]

        for lnet_configuration in lnet_configurations:
            self.assertEqual(lnet_configuration["state"], "lnet_up")
