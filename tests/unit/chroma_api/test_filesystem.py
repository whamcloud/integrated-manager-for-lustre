import mock

from chroma_core.models import Command
from chroma_core.models.target import ManagedMgs
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import synthetic_host, synthetic_volume_full


class TestFilesystemResource(ChromaApiTestCase):
    def setUp(self):
        super(TestFilesystemResource, self).setUp()

        self.host = synthetic_host("myserver")

    def test_spider(self):
        self.spider_api()
        self.create_simple_filesystem(self.host)
        self.spider_api()

    def test_HYD1483(self):
        """Test that adding a second MGS to a host emits a useful error."""
        mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(self.host).id, name="MGS")
        mgt.save()

        new_mgt_volume = synthetic_volume_full(self.host)
        mdt_volume = synthetic_volume_full(self.host)
        ost_volume = synthetic_volume_full(self.host)

        response = self.api_client.post(
            "/api/filesystem/",
            data={
                "name": "testfs",
                "mgt": {"volume_id": new_mgt_volume.id},
                "mdts": [{"volume_id": mdt_volume.id, "conf_params": {}}],
                "osts": [{"volume_id": ost_volume.id, "conf_params": {}}],
                "conf_params": {},
            },
        )
        self.assertHttpBadRequest(response)

        errors = self.deserialize(response)
        self.assertIn("only one MGS is allowed per server", errors["mgt"]["volume_id"][0])

    def test_set_state_partial(self):
        """Test operations using partial PUT containing only the state attribute, as used in Chroma 1.0.0.0 GUI"""
        self.create_simple_filesystem(self.host)
        fs_uri = "/api/filesystem/%s/" % self.fs.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_partial(fs_uri, "stopped")
            Command.set_state.assert_called_once()

    def test_set_state_full(self):
        """Test operations using fully populated PUTs"""
        self.create_simple_filesystem(self.host)
        fs_uri = "/api/filesystem/%s/" % self.fs.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_full(fs_uri, "stopped")
            Command.set_state.assert_called_once()
