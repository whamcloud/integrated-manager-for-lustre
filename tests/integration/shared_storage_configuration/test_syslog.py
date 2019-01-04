import time
from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
import uuid


class TestSyslog(ChromaIntegrationTestCase):
    def test_injected_message(self):
        hosts = self.add_hosts([config["lustre_servers"][0]["address"]])
        host = hosts[0]
        test_message = "%s" % uuid.uuid4()
        self.remote_operations.inject_log_message(host["fqdn"], test_message)

        TIMEOUT = 20
        elapsed = 0
        while True:
            response = self.chroma_manager.get("/api/log/", params={"message__contains": test_message})
            log_messages = response.json["objects"]
            if log_messages:
                self.assertEqual(len(log_messages), 1)
                log_message = log_messages[0]
                self.assertEqual(log_message["message"], test_message)
                self.assertEqual(log_message["fqdn"], host["fqdn"])
                break
            else:
                elapsed += 1
                time.sleep(1)
                if elapsed >= TIMEOUT:
                    raise AssertionError("Log message %s/%s did not appear" % (host["fqdn"], test_message))
