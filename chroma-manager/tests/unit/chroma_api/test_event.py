from chroma_core.models.log import Systemevents
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase

from tests.unit.chroma_core.lib.test_systemevents import examples


class TestTargetResource(ChromaApiTestCase):
    def test_syslogevents_render(self):
        log_count = 0
        for handler, log_examples in examples.items():
            for log_example in log_examples:
                handler(Systemevents.objects.create(message=log_example['message']), None)
                log_count += 1

        response = self.api_client.get("/api/event/", params = {'limit': 0})
        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(log_count, len(objects))
