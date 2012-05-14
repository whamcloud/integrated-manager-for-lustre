import dateutil.parser
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase


class TestMisc(ChromaApiTestCase):
    def test_HYD648(self):
        """Test that datetimes in the API have a timezone"""
        response = self.api_client.get("/api/host/")
        self.assertHttpOK(response)
        host = self.deserialize(response)['objects'][0]
        t = dateutil.parser.parse(host['state_modified_at'])
        self.assertNotEqual(t.tzinfo, None)
