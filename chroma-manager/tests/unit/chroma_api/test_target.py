from chroma_core.models import Command
import mock
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helper import fake_log_message, synthetic_host, synthetic_volume_full, create_target_patch


class TestTargetResource(ChromaApiTestCase):
    @create_target_patch
    def test_HYD965(self):
        """Test that targets cannot be added using volumes which are already in use"""
        host = synthetic_host('myserver')
        self.create_simple_filesystem(host)

        spare_volume = synthetic_volume_full(host)

        response = self.api_client.post("/api/target/", data = {
            'kind': 'OST',
            'filesystem_id': self.fs.id,
            'volume_id': spare_volume.id
        })
        self.assertHttpAccepted(response)

        response = self.api_client.post("/api/target/", data = {
            'kind': 'OST',
            'filesystem_id': self.fs.id,
            'volume_id': spare_volume.id
        })
        self.assertHttpBadRequest(response)

    def test_set_state_partial(self):
        """Test operations using partial PUT containing only the state attribute, as used in Chroma 1.0.0.0 GUI"""
        host = synthetic_host('myserver')
        self.create_simple_filesystem(host)
        mgt_uri = "/api/target/%s/" % self.mgt.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_partial(mgt_uri, 'unmounted')
            Command.set_state.assert_called_once()

    def test_set_state_full(self):
        """Test operations using a fully populated PUT"""
        host = synthetic_host('myserver')
        self.create_simple_filesystem(host)
        mgt_uri = "/api/target/%s/" % self.mgt.id
        with mock.patch("chroma_core.models.Command.set_state", mock.Mock(return_value=None)):
            self.api_set_state_full(mgt_uri, 'unmounted')
            Command.set_state.assert_called_once()

    def test_log_links(self):
        """Test that log viewer only displays valid links."""
        host = synthetic_host('myserver', ['192.168.0.1@tcp0'])
        self.create_simple_filesystem(host)
        fake_log_message('192.168.0.1@tcp testfs-MDT0000')
        response = self.api_client.get('/api/log/')
        event, = self.deserialize(response)['objects']
        self.assertEqual(len(event['substitutions']), 2)
        host.state = 'removed'
        host.save()
        self.mdt.not_deleted = False
        self.mdt.save()
        response = self.api_client.get('/api/log/')
        event, = self.deserialize(response)['objects']
        self.assertEqual(len(event['substitutions']), 0)
