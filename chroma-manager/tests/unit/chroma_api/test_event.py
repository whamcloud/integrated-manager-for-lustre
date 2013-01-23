from chroma_core.services.syslog.parser import client_connection_handler, admin_client_eviction_handler, client_eviction_handler
from chroma_core.models.event import Event
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCaseHeavy
from tests.unit.chroma_core.helper import fake_log_message

from tests.unit.chroma_core.lib.test_log_message import examples


class TestTargetResource(ChromaApiTestCaseHeavy):
    def test_syslogevents_render(self):
        e1 = Event.objects.count()

        log_count = 0
        for handler in [client_connection_handler, admin_client_eviction_handler, client_eviction_handler]:
            log_examples = examples[handler]
            for log_example in log_examples:
                handler(fake_log_message(log_example['message']), None)
                log_count += 1

        response = self.api_client.get("/api/event/", params = {'limit': 0})
        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(Event.objects.count(), len(objects))
        self.assertEqual(log_count, len(objects) - e1)
