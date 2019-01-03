from testconfig import config
from tests.integration.installation_and_upgrade.test_installation_and_upgrade import TestInstallationAndUpgrade


class TestCreateFilesystem(TestInstallationAndUpgrade):
    def add_hosts(self, addresses, auth_type="existing_keys_choice"):
        # Override add hosts functionality for older APIs

        # if the host_profile api endpoint exists can use current logic
        response = self.chroma_manager.get("/api/host_profile/")
        if response.successful:
            new_hosts = super(TestCreateFilesystem, self).add_hosts(addresses, auth_type)
        else:
            # otherwise we need to use the old way of adding hosts
            host_create_command_ids = []
            for host_address in addresses:
                profile = self.get_best_host_profile(host_address)
                response = self.chroma_manager.post(
                    "/api/test_host/", body={"address": host_address, "server_profile": profile["resource_uri"]}
                )
                self.assertTrue(response.successful, response.text)
                response = self.chroma_manager.post(
                    "/api/host/", body={"address": host_address, "server_profile": profile["resource_uri"]}
                )
                self.assertTrue(response.successful, response.text)
                host_create_command_ids.append(response.json["command"]["id"])
            self.wait_for_commands(self.chroma_manager, host_create_command_ids, timeout=1800)
            new_hosts = self.get_hosts(addresses)

        self.assertEqual(len(new_hosts), len(addresses), "Hosts found: '%s'" % new_hosts)
        self.remote_operations.sync_disks([h["address"] for h in new_hosts])
        self.remote_operations.catalog_rpms([h["address"] for h in new_hosts], "/tmp/rpms_before_upgrade", sorted=True)

        return new_hosts

    def _exercise_simple(self, fs_id):
        filesystem = self.get_filesystem(fs_id)
        client = config["lustre_clients"][0]["address"]
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_operations.exercise_filesystem(client, filesystem)
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

    def test_create(self):
        """ Test that a filesystem can be created"""
        filesystem_id = self.create_filesystem_standard(config["lustre_servers"][0:4])

        self._exercise_simple(filesystem_id)

        self.assertTrue(self.get_filesystem_by_name(self.fs_name)["name"] == self.fs_name)


class TestAddHost(TestCreateFilesystem):
    def test_add_host(self):
        """ Test that a host and OST can be added to a filesystem"""

        filesystem_id = self.get_filesystem_by_name(self.fs_name)["id"]
        filesystem_uri = "/api/filesystem/%s/" % filesystem_id

        new_hosts = self.add_hosts([config["lustre_servers"][2]["address"], config["lustre_servers"][3]["address"]])

        ost_volume = self.wait_for_shared_volumes(1, 4)

        self.set_volume_mounts(ost_volume, new_hosts[0]["id"], new_hosts[1]["id"])

        # add the new volume to the existing filesystem
        response = self.chroma_manager.post(
            "/api/target/", body={"volume_id": ost_volume["id"], "kind": "OST", "filesystem_id": filesystem_id}
        )
        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json["target"]["resource_uri"]
        create_command = response.json["command"]["id"]
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, "mounted")
        self.assertState(filesystem_uri, "available")

        self.assertEqual(len(self.chroma_manager.get("/api/filesystem/").json["objects"][0]["osts"]), 2)


class TestExistsFilesystem(TestCreateFilesystem):
    def test_exists(self):
        filesystem = self.get_filesystem_by_name(self.fs_name)
        self.assertTrue(filesystem["name"] == self.fs_name)
        # start it up since it was stopped before the upgrade
        self.start_filesystem(filesystem["id"])
        # wait for it to be available, in case we rebooted storage servers before getting here
        self.wait_until_true(lambda: self.get_filesystem_by_name(self.fs_name)["state"] == "available")
        self._exercise_simple(filesystem["id"])
