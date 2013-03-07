from chroma_core.services.syslog.parser import client_connection_handler, admin_client_eviction_handler, client_eviction_handler
from chroma_core.models.event import Event

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.services.syslog.test_handlers import examples


class TestTargetResource(ChromaApiTestCase):
    def test_syslogevents_render(self):
        e1 = Event.objects.count()

        log_count = 0
        for handler in [client_connection_handler, admin_client_eviction_handler, client_eviction_handler]:
            log_examples = examples[handler]
            for log_example in log_examples:
                handler(log_example['message'], None)
                log_count += 1

        response = self.api_client.get("/api/event/", params = {'limit': 0})
        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(Event.objects.count(), len(objects))
        self.assertEqual(log_count, len(objects) - e1)
