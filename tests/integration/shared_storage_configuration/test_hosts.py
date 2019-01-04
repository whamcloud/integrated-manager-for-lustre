from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestHosts(ChromaIntegrationTestCase):
    def test_hosts_add_existing_filesystem(self):
        # Create a file system and then add new hosts/volumes to it
        host_addresses = [h["address"] for h in config["lustre_servers"][:2]]
        hosts = self.add_hosts(host_addresses)
        self.configure_power_control(host_addresses)

        volumes = self.wait_for_shared_volumes(3, 2)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volume = volumes[2]
        self.set_volume_mounts(mgt_volume, hosts[0]["id"], hosts[1]["id"])
        self.set_volume_mounts(mdt_volume, hosts[0]["id"], hosts[1]["id"])
        self.set_volume_mounts(ost_volume, hosts[1]["id"], hosts[0]["id"])

        filesystem_id = self.create_filesystem(
            hosts,
            {
                "name": "testfs",
                "mgt": {"volume_id": mgt_volume["id"]},
                "mdts": [{"volume_id": mdt_volume["id"], "conf_params": {}}],
                "osts": [{"volume_id": ost_volume["id"], "conf_params": {}}],
                "conf_params": {},
            },
        )

        filesystem_uri = "/api/filesystem/%s/" % filesystem_id

        self.add_hosts([config["lustre_servers"][2]["address"]])

        remaining_volumes = self.wait_usable_volumes(len(volumes) - 3)
        self.assertEqual(len(volumes) - 3, len(remaining_volumes))

        # add the new volume to the existing filesystem
        response = self.chroma_manager.post(
            "/api/target/",
            body={"volume_id": remaining_volumes[0]["id"], "kind": "OST", "filesystem_id": filesystem_id},
        )
        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json["target"]["resource_uri"]
        create_command = response.json["command"]["id"]
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, "mounted")
        self.assertState(filesystem_uri, "available")

        self.assertEqual(len(self.chroma_manager.get("/api/filesystem/").json["objects"][0]["osts"]), 2)
