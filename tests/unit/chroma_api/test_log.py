from django.contrib.auth.models import User, Group

from tests.unit.chroma_api.tastypie_test import TestApiClient
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import fake_log_message


class TestLogResource(ChromaApiTestCase):
    def setUp(self):
        super(TestLogResource, self).setUp()

        # create users for filesystem_users test
        filesystem_user = User.objects.create_user("test_filesystem_user", "", "password")
        filesystem_user.groups.add(Group.objects.get(name="filesystem_users"))

        self.clients = {
            "superuser": self.api_client,
            "filesystem_user": TestApiClient(),
            "filesystem_administrator": TestApiClient(),
            "unauthenticated": TestApiClient(),
        }

        # authenticate clients
        self.assertTrue(
            self.clients["filesystem_user"].client.login(username="test_filesystem_user", password="password")
        )
        self.assertTrue(self.clients["filesystem_administrator"].client.login(username="debug", password="lustre"))

        # some basic log entries
        # all Lustre log entries have a leading space.
        self.messages = ["Plain old log message", "Lustre: Normal Lustre Message", "LustreError: Lustre Error Message"]
        self.lustre_messages = [message for message in self.messages if message.startswith("Lustre")]
        for message in self.messages:
            fake_log_message(message)

    def test_get_logs_lustre_only(self):
        """Verifies unauthenticated users and filesystem_users only get lustre messages"""

        for client_key in ["filesystem_user", "unauthenticated"]:
            client = self.clients[client_key]
            log_entries = [log_entry["message"] for log_entry in self.deserialize(client.get("/api/log/"))["objects"]]
            xs = self.lustre_messages[::-1]
            self.assertListEqual(xs, log_entries)

    def test_get_logs_all(self):
        """Verifies superusers and filesystem_administrators gets all log entries"""

        for client_key in ["filesystem_administrator", "superuser"]:
            client = self.clients[client_key]
            log_entries = [log_entry["message"] for log_entry in self.deserialize(client.get("/api/log/"))["objects"]]
            xs = self.messages[::-1]
            self.assertListEqual(xs, log_entries)
