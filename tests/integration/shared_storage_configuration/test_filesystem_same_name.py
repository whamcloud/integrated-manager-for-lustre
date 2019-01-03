from tests.integration.core.constants import LONG_TEST_TIMEOUT
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestFilesystemSameNameHYD832(ChromaIntegrationTestCase):
    def test_same_name(self):
        """
        Test that creating a filesystem with the same name as a
        previously removed filesystem on the same MGS.
        """
        self.assertGreaterEqual(len(self.TEST_SERVERS[0]["device_paths"]), 5)

        reused_name = "testfs"
        other_name = "foofs"

        # The test uses a custom filesystem creation using 3 disks instead of the
        # usual 4 because we need the other 2 disks for later in the test.
        host_addresses = [s["address"] for s in self.TEST_SERVERS[:4]]
        hosts = self.add_hosts(host_addresses)

        # Since the test code seems to rely on this ordering, we should
        # check for it right away and blow up if it's not as we expect.
        self.assertEqual([h["address"] for h in hosts], host_addresses)

        self.configure_power_control(host_addresses)

        ha_volumes = self.wait_for_shared_volumes(5, 4)

        self.set_volume_mounts(ha_volumes[0], hosts[0]["id"], hosts[1]["id"])
        self.set_volume_mounts(ha_volumes[1], hosts[0]["id"], hosts[1]["id"])
        self.set_volume_mounts(ha_volumes[2], hosts[1]["id"], hosts[0]["id"])

        fs_id = self.create_filesystem(
            hosts[:2],
            {
                "name": reused_name,
                "mgt": {"volume_id": ha_volumes[0]["id"]},
                "mdts": [{"volume_id": ha_volumes[1]["id"], "conf_params": {}}],
                "osts": [{"volume_id": ha_volumes[2]["id"], "conf_params": {}}],
                "conf_params": {},
            },
        )

        fs = self.chroma_manager.get("/api/filesystem/%s/" % fs_id, params={"dehydrate__osts": True}).json
        mgt_id = fs["mgt"]["id"]

        def create_for_mgs(name, hosts_to_use, reformat=False):
            ha_volumes = self.wait_for_shared_volumes(2, 4)

            self.set_volume_mounts(ha_volumes[0], hosts_to_use[0]["id"], hosts_to_use[1]["id"])
            self.set_volume_mounts(ha_volumes[1], hosts_to_use[1]["id"], hosts_to_use[0]["id"])

            mdt_volume = ha_volumes[0]
            ost_volumes = [ha_volumes[1]]
            return self.create_filesystem(
                hosts_to_use,
                {
                    "name": name,
                    "mgt": {"id": mgt_id},
                    "mdts": [{"volume_id": mdt_volume["id"], "conf_params": {}, "reformat": reformat}],
                    "osts": [{"volume_id": v["id"], "conf_params": {}, "reformat": reformat} for v in ost_volumes],
                    "conf_params": {},
                },
            )

        other_fs_id = create_for_mgs(other_name, hosts[2:4])

        response = self.chroma_manager.delete(fs["resource_uri"])
        self.assertEqual(response.status_code, 202)
        self.wait_for_command(self.chroma_manager, response.json["command"]["id"], timeout=LONG_TEST_TIMEOUT)

        # Now remove any zfs datasets, this is a topic to be discussed, but until we remove the datasets
        # we cannot create a new filesystem. If IML does it directly as part of remove filesystem which it could
        # then removing the filesystem would be truly unrecoverable and people might not like that.
        datasets = [ost["volume"]["volume_nodes"][0]["path"] for ost in fs["osts"]]
        datasets.extend([mdt["volume"]["volume_nodes"][0]["path"] for mdt in fs["mdts"]])

        # Filter out the paths by removing anything with a leading /.
        datasets = [dataset for dataset in datasets if dataset.startswith("/") is False]
        datasets.sort(key=lambda x: -len(x))

        pools = map(lambda x: x.split("/")[0], datasets)

        fqdns = [x["fqdn"] for x in self.TEST_SERVERS[:4]]

        for pool in pools:
            self.execute_commands(
                ["zpool import %s" % pool], fqdns[0], "import pool %s" % pool, expected_return_code=None
            )

        for zpool_dataset in datasets:
            self.execute_commands(
                ["zfs destroy %s" % zpool_dataset],
                fqdns[0],
                "destroy zfs dataset %s" % zpool_dataset,
                expected_return_code=None,
            )

        # Our other FS should be untouched
        self.assertEqual(len(self.chroma_manager.get("/api/filesystem/").json["objects"]), 1)
        self.assertState("/api/filesystem/%s/" % other_fs_id, "available")

        reused_fs_id = create_for_mgs(reused_name, hosts[:2], reformat=True)

        self.assertState("/api/filesystem/%s/" % reused_fs_id, "available")
        self.assertState("/api/filesystem/%s/" % other_fs_id, "available")

        self.graceful_teardown(self.chroma_manager)
