from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestVolumes(ChromaIntegrationTestCase):
    # def test_volumes_on_existing_filesystem_not_usable(self):
    #     # Testing that volumes mounted on a server known to Chroma
    #     # are not included in the list of usable volumes. Repro of HYD-1669.
    #     # Create a file system.
    #     host_addresses = [config['lustre_servers'][0]['address']]
    #     hosts = self.add_hosts(host_addresses)
    #     self.configure_power_control(host_addresses)
    #
    #     ha_volumes = self.get_usable_volumes()
    #     self.assertGreaterEqual(len(ha_volumes), 3)
    #
    #     mgt_volume = ha_volumes[0]
    #     mdt_volume = ha_volumes[1]
    #     ost_volumes = [ha_volumes[2]]
    #     self.create_filesystem(hosts,
    #                            {'name': 'testfs',
    #                             'mgt': {'volume_id': mgt_volume['id']},
    #                             'mdt': {
    #                                 'volume_id': mdt_volume['id'],
    #                                 'conf_params': {}},
    #                             'osts': [{
    #                                 'volume_id': v['id'],
    #                                 'conf_params': {}
    #                             } for v in ost_volumes],
    #                             'conf_params': {}})
    #     host_id = self.chroma_manager.get("/api/host").json['objects'][0]['id']
    #
    #     # Force remove the hosts (and thus the file system) so that they are
    #     # forgotten from the db but not actually torn down.
    #     command = self.chroma_manager.post("/api/command/", body = {
    #         'jobs': [{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host_id}}],
    #         'message': "Test force remove hosts"
    #     }).json
    #     self.wait_for_command(self.chroma_manager, command['id'])
    #     self.assertEqual(len(self.chroma_manager.get("/api/host").json['objects']), 0)
    #
    #     # Re-add the removed hosts
    #     self.add_hosts([config['lustre_servers'][0]['address']])
    #
    #     # Verify that the used volumes aren't showing as usable volumes.
    #     usable_volumes_labels = [v['label'] for v in self.get_usable_volumes()]
    #     self.assertNotIn(mgt_volume['label'], usable_volumes_labels)
    #     self.assertNotIn(mdt_volume['label'], usable_volumes_labels)
    #     self.assertNotIn(ost_volumes[0]['label'], usable_volumes_labels)

    def test_volumes_cleared_on_teardown(self):
        # Create a file system and then tear down the manager, then verify
        # after tear down that the volumes from the file system no longer
        # appear in the database. Repro of HYD-1143.
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

        self.create_filesystem(
            hosts,
            {
                "name": "testfs",
                "mgt": {"volume_id": mgt_volume["id"]},
                "mdts": [{"volume_id": mdt_volume["id"], "conf_params": {}}],
                "osts": [{"volume_id": ost_volume["id"], "conf_params": {}}],
                "conf_params": {},
            },
        )

        self.graceful_teardown(self.chroma_manager)

        response = self.chroma_manager.get("/api/volume/", params={"limit": 0})
        self.assertTrue(response.successful, response.text)
        volumes = response.json["objects"]
        self.assertEqual(0, len(volumes))
