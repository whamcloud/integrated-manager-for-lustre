from unittest import skip
from testconfig import config

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestFilesystemDNE(ChromaIntegrationTestCase):
    def setUp(self):
        super(TestFilesystemDNE, self).setUp()

    def _set_mount(self, volume):
        # FIXME: Should switch primary host for each volume based on even/odd id to mimic real-life distribution
        #        of volumes for load balancing purposes
        # host_id = int(volume['id']) % 2
        host_id = 0
        self.set_volume_mounts(volume, self.hosts[host_id]["id"], self.hosts[host_id | 1]["id"])

    def _create_filesystem(self, mdt_count):
        assert mdt_count in [1, 2, 3]

        host_addresses = [h["address"] for h in config["lustre_servers"][:2]]
        self.hosts = self.add_hosts(host_addresses)

        # Since the test code seems to rely on this ordering, we should
        # check for it right away and blow up if it's not as we expect.
        self.assertEqual([h["address"] for h in self.hosts], host_addresses)

        self.configure_power_control(host_addresses)

        self.ha_volumes = self.wait_for_shared_volumes(5, 2)

        mgt_volume = self.ha_volumes[0]
        mdt_volumes = self.ha_volumes[1 : (1 + mdt_count)]
        ost_volumes = self.ha_volumes[4:5]

        map(self._set_mount, [mgt_volume] + mdt_volumes + ost_volumes)

        self.filesystem_id = self.create_filesystem(
            self.hosts,
            {
                "name": "testfs",
                "mgt": {"volume_id": mgt_volume["id"], "conf_params": {}, "reformat": True},
                "mdts": [{"volume_id": v["id"], "conf_params": {}, "reformat": True} for v in mdt_volumes],
                "osts": [{"volume_id": v["id"], "conf_params": {}, "reformat": True} for v in ost_volumes],
                "conf_params": {},
            },
        )

        return self.get_filesystem(self.filesystem_id)

    def _add_mdt(self, index, mdt_count):
        mdt_volumes = self.ha_volumes[1 + index : (1 + index + mdt_count)]
        create_commands = []

        for mdt_volume in mdt_volumes:
            response = self.chroma_manager.post(
                "/api/target/", body={"volume_id": mdt_volume["id"], "kind": "MDT", "filesystem_id": self.filesystem_id}
            )

            self.assertEqual(response.status_code, 202, response.text)
            create_commands.append(response.json["command"]["id"])

        for create_command in create_commands:
            self.wait_for_command(self.chroma_manager, create_command)

        return self.chroma_manager.get("/api/filesystem", params={"id": self.filesystem_id}).json["objects"][0]

    def _delete_mdt(self, filesystem, mdt, fail=False):
        response = self.chroma_manager.delete(mdt["resource_uri"])

        if fail:
            self.assertEqual(response.status_code, 400, response.text)
            self.assertTrue("State 'removed' is invalid" in response.text, response.text)
        else:
            self.assertEqual(response.status_code, 202, response.text)
            self.wait_for_command(self.chroma_manager, response.json["command"]["id"])

        return self.chroma_manager.get("/api/filesystem", params={"id": self.filesystem_id}).json["objects"][0]

    def test_create_dne_filesystem(self):
        """
        Test that we can create a DNE file system with 2 MDTs
        """
        filesystem = self._create_filesystem(2)
        self.assertEqual(len(filesystem["mdts"]), 2)
        self.assertEqual(len(filesystem["osts"]), 1)

    @skip("Remove while we fix HYD-4520")
    def test_create_single_filesystem_add_mdt(self):
        """
        Test that we can create a single MDT file system and then add MDTs
        """
        filesystem = self._create_filesystem(1)
        self.assertEqual(len(filesystem["mdts"]), 1)
        self.assertEqual(len(filesystem["osts"]), 1)

        filesystem = self._add_mdt(1, 1)
        self.assertEqual(len(filesystem["mdts"]), 2)
        self.assertEqual(len(filesystem["osts"]), 1)

        filesystem = self._add_mdt(2, 1)
        self.assertEqual(len(filesystem["mdts"]), 3)
        self.assertEqual(len(filesystem["osts"]), 1)

    def test_mdt0_undeletable(self):
        """
        Test to ensure that we cannot delete MDT0
        """
        filesystem = self._create_filesystem(3)
        self.assertEqual(len(filesystem["mdts"]), 3)
        self.assertEqual(len(filesystem["osts"]), 1)

        filesystem = self._delete_mdt(
            filesystem, next(mdt for mdt in filesystem["mdts"] if mdt["index"] == 0), fail=True
        )
        self.assertEqual(len(filesystem["mdts"]), 3)
        self.assertEqual(len(filesystem["osts"]), 1)

        # Remove for HYD-4419 which removed the ability to remove an MDT
        # filesystem = self._delete_mdt(filesystem, next(mdt for mdt in filesystem['mdts'] if mdt['index'] != 0), fail = False)
        # self.assertEqual(len(filesystem['mdts']), 2)
        # self.assertEqual(len(filesystem['osts']), 1)

        # For HYD-4419 check that an INDEX != 0 also can't be removed.
        filesystem = self._delete_mdt(
            filesystem, next(mdt for mdt in filesystem["mdts"] if mdt["index"] != 0), fail=True
        )
        self.assertEqual(len(filesystem["mdts"]), 3)
        self.assertEqual(len(filesystem["osts"]), 1)

    @skip("LU-6586 Prevents DNE Removal Working")
    def test_mdt_add_delete_add(self):
        """
        Test to ensure that we add and delete MDTs
        """
        filesystem = self._create_filesystem(1)
        self.assertEqual(len(filesystem["mdts"]), 1)
        self.assertEqual(len(filesystem["osts"]), 1)

        filesystem = self._add_mdt(1, 2)
        self.assertEqual(len(filesystem["mdts"]), 3)
        self.assertEqual(len(filesystem["osts"]), 1)

        filesystem = self._delete_mdt(
            filesystem, next(mdt for mdt in filesystem["mdts"] if mdt["index"] == 2), fail=False
        )
        self.assertEqual(len(filesystem["mdts"]), 2)
        self.assertEqual(len(filesystem["osts"]), 1)

        filesystem = self._add_mdt(1, 1)
        self.assertEqual(len(filesystem["mdts"]), 3)
        self.assertEqual(len(filesystem["osts"]), 1)

        # The new one should have an index of 3 (being the 4th added) so check by finding.
        # This will exception if there is no index == 3
        next(mdt for mdt in filesystem["mdts"] if mdt["index"] == 3)
