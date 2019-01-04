from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestWriteconf(ChromaIntegrationTestCase):
    def _exercise_simple(self, fs_id):
        filesystem = self.get_filesystem(fs_id)
        client = config["lustre_clients"][0]["address"]
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_operations.exercise_filesystem(client, filesystem)
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

    def testUpdateNids(self):
        """Test that running UpdateNids on a filesystem leaves it in a working state,
           note: we're not actually *changing* any NIDs here, just exercising the code.
           CRG: I have left this test in but with the UpdateNids removed because we don't
           require it anymore. We still validate some stuff works, but someone might decide
           to just remove this file"""
        self.assertGreaterEqual(len(self.config_servers), 4)

        host_addresses = [h["address"] for h in config["lustre_servers"][:4]]
        self.hosts = self.add_hosts(host_addresses)
        self.configure_power_control(host_addresses)

        volumes = self.wait_for_shared_volumes(4, 4)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volume = volumes[2]
        self.set_volume_mounts(mgt_volume, self.hosts[0]["id"], self.hosts[1]["id"])
        self.set_volume_mounts(mdt_volume, self.hosts[0]["id"], self.hosts[1]["id"])
        self.set_volume_mounts(ost_volume, self.hosts[2]["id"], self.hosts[3]["id"])

        self.filesystem_id = self.create_filesystem(
            self.hosts,
            {
                "name": "testfs",
                "mgt": {"volume_id": mgt_volume["id"]},
                "mdts": [{"volume_id": mdt_volume["id"], "conf_params": {}}],
                "osts": [{"volume_id": ost_volume["id"], "conf_params": {}}],
                "conf_params": {},
            },
        )

        self._exercise_simple(self.filesystem_id)

        response = self.chroma_manager.post(
            "/api/command/", body={"jobs": [{"class_name": "UpdateNidsJob", "args": {}}], "message": "Test writeconf"}
        )
        self.assertEqual(response.status_code, 201)
        command = response.json
        self.wait_for_command(self.chroma_manager, command["id"])

        # Writeconf will leave the filesystem down, so bring it up again
        self.set_state("/api/filesystem/%s/" % self.filesystem_id, "available")

        self._exercise_simple(self.filesystem_id)
