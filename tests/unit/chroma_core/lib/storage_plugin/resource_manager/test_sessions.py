from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestSessions(ResourceManagerTestCase):
    def setUp(self):
        super(TestSessions, self).setUp("example_plugin")

        resource_class, resource_class_id = self.manager.get_plugin_resource_class("example_plugin", "Couplet")
        record, created = StorageResourceRecord.get_or_create_root(
            resource_class, resource_class_id, {"address_1": "192.168.0.1", "address_2": "192.168.0.2"}
        )

        self.scannable_resource_id = record.pk

    def test_open_close(self):
        self.assertEqual(len(self.resource_manager._sessions), 0)

        # Create a new session (clean slate)
        self.resource_manager.session_open(self.plugin, self.scannable_resource_id, [], 60)
        self.assertEqual(len(self.resource_manager._sessions), 1)

        # Create a new session (override previous)
        self.resource_manager.session_open(self.plugin, self.scannable_resource_id, [], 60)
        self.assertEqual(len(self.resource_manager._sessions), 1)

        # Close a session
        self.resource_manager.session_close(self.scannable_resource_id)
        self.assertEqual(len(self.resource_manager._sessions), 0)

        # Check that it's allowed to close a non-existent session
        # (plugins don't have to guarantee opening before calling
        # closing in a finally block)
        self.resource_manager.session_close(self.scannable_resource_id)
        self.assertEqual(len(self.resource_manager._sessions), 0)
