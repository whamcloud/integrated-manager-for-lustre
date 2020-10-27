import json

import mock

from chroma_core.models import Command, Nid
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import (
    fake_log_message,
    synthetic_host,
    synthetic_volume_full,
    create_targets_patch,
    create_filesystem_patch,
)


class TestTargetResource(ChromaApiTestCase):
    @create_targets_patch
    def test_HYD965(self):
        """Test that targets cannot be added using volumes which are already in use"""
        host = synthetic_host("myserver")
        self.create_simple_filesystem(host)

        spare_volume = synthetic_volume_full(host)

        response = self.api_client.post(
            "/api/target/", data={"kind": "OST", "filesystem_id": self.fs.id, "volume_id": spare_volume.id}
        )
        self.assertHttpAccepted(response)

        response = self.api_client.post(
            "/api/target/", data={"kind": "OST", "filesystem_id": self.fs.id, "volume_id": spare_volume.id}
        )
        self.assertHttpBadRequest(response)

    @create_targets_patch
    def test_post_creation(self):
        """Test that creating an OST using POST returns a target and a command"""
        host = synthetic_host("myserver")
        self.create_simple_filesystem(host)

        spare_volume = synthetic_volume_full(host)

        response = self.api_client.post(
            "/api/target/", data={"kind": "OST", "filesystem_id": self.fs.id, "volume_id": spare_volume.id}
        )
        self.assertHttpAccepted(response)

    @create_targets_patch
    def test_patch_creation(self):
        """Test that creating multiple Targets using PATCH returns a target and a command"""
        host = synthetic_host("myserver")
        self.create_simple_filesystem(host)

        spare_volume_1 = synthetic_volume_full(host)
        spare_volume_2 = synthetic_volume_full(host)

        response = self.api_client.patch(
            "/api/target/",
            data={
                "objects": [
                    {"kind": "OST", "filesystem_id": self.fs.id, "volume_id": spare_volume_1.id},
                    {"kind": "MDT", "filesystem_id": self.fs.id, "volume_id": spare_volume_2.id},
                ],
                "deletions": [],
            },
        )
        self.assertHttpAccepted(response)

    def test_set_state_partial(self):
        """Test operations using partial PUT containing only the state attribute, as used in Chroma 1.0.0.0 GUI"""
        host = synthetic_host("myserver")
        self.create_simple_filesystem(host)
        mgt_uri = "/api/target/%s/" % self.mgt.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_partial(mgt_uri, "unmounted")
            Command.set_state.assert_called_once()

    def test_set_state_full(self):
        """Test operations using a fully populated PUT"""
        host = synthetic_host("myserver")
        self.create_simple_filesystem(host)
        mgt_uri = "/api/target/%s/" % self.mgt.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_full(mgt_uri, "unmounted")
            Command.set_state.assert_called_once()

    def _target_hosts(self, paths):
        """Generate host labels for given target paths."""
        for path in paths:
            response = self.api_client.get(path)
            self.assertHttpOK(response)
            content = json.loads(response.content)
            (volume_node,) = content["volume"]["volume_nodes"]
            yield volume_node["host_label"]

    @create_targets_patch
    def test_striping_patch(self):
        """Test OSTs are assigned to alternating hosts."""
        self.create_simple_filesystem(synthetic_host("myserver"))
        hosts = [synthetic_host("myserver{0:d}".format(n)) for n in range(4)] * 2
        # keep hosts in alternating order, but supply them grouped
        objects = [
            {"kind": "OST", "filesystem_id": self.fs.id, "volume_id": synthetic_volume_full(host).id}
            for host in sorted(hosts, key=str)
        ]
        response = self.api_client.patch("/api/target/", data={"deletions": [], "objects": objects})
        self.assertHttpAccepted(response)
        content = json.loads(response.content)
        self.assertEqual(map(str, hosts), list(self._target_hosts(content["targets"])))

    @create_filesystem_patch
    def test_striping_post(self):
        """Test OSTs are assigned to alternating hosts."""
        self.host = synthetic_host("myserver")
        hosts = [synthetic_host("myserver{0:d}".format(n)) for n in range(4)] * 2
        # keep hosts in alternating order, but supply them grouped
        data = {
            "name": "testfs",
            "mgt": {"volume_id": synthetic_volume_full(self.host).id, "conf_params": {}},
            "mdts": [{"volume_id": synthetic_volume_full(self.host).id, "conf_params": {}}],
            "osts": [
                {"volume_id": synthetic_volume_full(host).id, "conf_params": {}} for host in sorted(hosts, key=str)
            ],
            "conf_params": {},
        }
        response = self.api_client.post("/api/filesystem/", data=data)
        self.assertHttpAccepted(response)
        content = json.loads(response.content)
        self.assertEqual(map(str, hosts), list(self._target_hosts(content["filesystem"]["osts"])))

    @create_targets_patch
    def test_select_by_filesystem(self):
        """Test selecting target by filesystem with valid and invalid filesystem ids."""
        self.create_simple_filesystem(synthetic_host("myserver"))

        response = self.api_client.get("/api/target/", data={"filesystem_id": self.fs.id})
        self.assertHttpOK(response)
        content = json.loads(response.content)
        self.assertEqual(3, len(content["objects"]))

        response = self.api_client.get("/api/target/", data={"filesystem_id": -1000})
        self.assertHttpOK(response)
        content = json.loads(response.content)
        self.assertEqual(0, len(content["objects"]))
