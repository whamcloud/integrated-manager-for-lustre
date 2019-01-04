from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestStartingAndStoppingTargets(ChromaIntegrationTestCase):
    def test_management_target_stops_and_starts(self):

        self.add_hosts([config["lustre_servers"][0]["address"]])
        volumes = self.get_usable_volumes()

        response = self.chroma_manager.post("/api/target/", body={"volume_id": volumes[0]["id"], "kind": "MGT"})
        self.assertEqual(response.status_code, 202)
        create_command = response.json["command"]["id"]
        self.wait_for_command(self.chroma_manager, create_command)
        target_uri = response.json["target"]["resource_uri"]
        mgt = self.get_json_by_uri(target_uri)
        host = self.get_list("/api/host/")[0]

        self.assertState(target_uri, "mounted")
        self.assertTrue(self.remote_operations.get_resource_running(host, mgt["ha_label"]))

        self.set_state(target_uri, "unmounted")
        self.assertFalse(self.remote_operations.get_resource_running(host, mgt["ha_label"]))

        self.set_state(target_uri, "mounted")
        self.assertTrue(self.remote_operations.get_resource_running(host, mgt["ha_label"]))

    def test_ost_and_mdt_stops_and_starts(self):

        self.create_filesystem_standard(self.TEST_SERVERS)

        ost_response = self.chroma_manager.get("/api/target", params={"kind": "OST"})
        mdt_response = self.chroma_manager.get("/api/target", params={"kind": "MDT"})
        self.assertEqual(ost_response.status_code, 200)
        self.assertEqual(mdt_response.status_code, 200)
        ost = ost_response.json["objects"][0]
        mdt = mdt_response.json["objects"][0]

        ost_host_response = self.chroma_manager.get(ost["active_host"])
        mdt_host_response = self.chroma_manager.get(mdt["active_host"])
        self.assertEqual(ost_host_response.status_code, 200)
        self.assertEqual(mdt_host_response.status_code, 200)
        ost_host = ost_host_response.json
        mdt_host = mdt_host_response.json

        self.assertState(ost["resource_uri"], "mounted")
        self.assertState(mdt["resource_uri"], "mounted")
        self.assertTrue(self.remote_operations.get_resource_running(ost_host, ost["ha_label"]))
        self.assertTrue(self.remote_operations.get_resource_running(mdt_host, mdt["ha_label"]))

        self.set_state(ost["resource_uri"], "unmounted")
        self.set_state(mdt["resource_uri"], "unmounted")
        self.assertFalse(self.remote_operations.get_resource_running(ost_host, ost["ha_label"]))
        self.assertFalse(self.remote_operations.get_resource_running(mdt_host, mdt["ha_label"]))

        self.set_state(ost["resource_uri"], "mounted")
        self.set_state(mdt["resource_uri"], "mounted")
        self.assertTrue(self.remote_operations.get_resource_running(ost_host, ost["ha_label"]))
        self.assertTrue(self.remote_operations.get_resource_running(mdt_host, mdt["ha_label"]))
