
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


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
