
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helper import fake_log_message


class TestTargetResource(ChromaApiTestCase):
    def test_HYD965(self):
        """Test that targets cannot be added using volumes which are already in use"""
        self.create_simple_filesystem()

        spare_volume = self._test_lun(self.host)

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

    def test_start_stop_partial(self):
        """Test operations using partial PUT containing only the state attribute, as used in Chroma 1.0.0.0 GUI"""
        self.create_simple_filesystem()
        mgt_uri = "/api/target/%s/" % self.mgt.id
        self.api_set_state_partial(mgt_uri, 'unmounted')
        self.api_set_state_partial(mgt_uri, 'mounted')
        self.api_set_state_partial(mgt_uri, 'unmounted')

    def test_start_stop_full(self):
        """Test operations using a fully populated PUT"""
        self.create_simple_filesystem()
        mgt_uri = "/api/target/%s/" % self.mgt.id
        self.api_set_state_full(mgt_uri, 'unmounted')
        self.api_set_state_full(mgt_uri, 'mounted')
        self.api_set_state_full(mgt_uri, 'unmounted')

    def test_log_links(self):
        """Test that log viewer only displays valid links."""
        self.create_simple_filesystem()
        fake_log_message('192.168.0.1@tcp testfs-MDT0000')
        response = self.api_client.get('/api/log/')
        event, = self.deserialize(response)['objects']
        self.assertEqual(len(event['substitutions']), 2)
        self.host.state = 'removed'
        self.host.save()
        self.mdt.not_deleted = False
        self.mdt.save()
        response = self.api_client.get('/api/log/')
        event, = self.deserialize(response)['objects']
        self.assertEqual(len(event['substitutions']), 0)
