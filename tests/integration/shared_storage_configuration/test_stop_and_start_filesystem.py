from testconfig import config
from collections import defaultdict
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestStartingAndStoppingTargets(ChromaIntegrationTestCase):
    def test_filesystem_stops_and_starts(self):
        filesystem_id = self.create_filesystem_standard(config["lustre_servers"][0:4])
        filesystem = self.get_filesystem(filesystem_id)

        target = defaultdict(list)
        host = defaultdict(list)

        for kind in ["osts", "mdts"]:
            for target_index in range(0, len(filesystem[kind])):
                if kind == "mdts":
                    target[kind].append(filesystem[kind][target_index])
                elif kind == "osts":
                    response = self.chroma_manager.get(filesystem[kind][target_index])
                    self.assertEqual(response.status_code, 200)
                    target[kind].append(response.json)

                host_response = self.chroma_manager.get(target[kind][target_index]["active_host"])
                self.assertEqual(host_response.status_code, 200)
                host[kind].append(host_response.json)

        self.assertState(filesystem["resource_uri"], "available")
        for kind in ["osts", "mdts"]:
            for target_index in range(0, len(filesystem[kind])):
                self.assertTrue(
                    self.remote_operations.get_resource_running(
                        host[kind][target_index], target[kind][target_index]["ha_label"]
                    )
                )

        for fs_state in ["stopped", "available"]:
            self.set_state(filesystem["resource_uri"], fs_state)
            for kind in ["osts", "mdts"]:
                for target_index in range(0, len(filesystem[kind])):
                    self.assertEqual(
                        fs_state == "available",
                        self.remote_operations.get_resource_running(
                            host[kind][target_index], target[kind][target_index]["ha_label"]
                        ),
                    )
