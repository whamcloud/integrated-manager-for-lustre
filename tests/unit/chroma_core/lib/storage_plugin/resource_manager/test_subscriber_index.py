from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestSubscriberIndex(ResourceManagerTestCase):
    def test_populate(self):
        """Test that the subscriber index is set up correctly for
        resources already in the database"""

        resource_record, scannable_resource = self._make_global_resource(
            "linux", "PluginAgentResources", {"plugin_name": "linux", "host_id": self.host.id}
        )

        scannable_resource_pk = resource_record.pk
        scannable_resource = scannable_resource

        dev_resource = self._make_local_resource("linux", "UnsharedDevice", path="/dev/foo", size=4096)
        node_resource = self._make_local_resource(
            "linux", "LinuxDeviceNode", path="/dev/foo", parents=[dev_resource], host_id=self.host.id
        )

        controller_record, controller_resource = self._make_global_resource(
            "subscription_plugin", "Controller", {"address": "192.168.0.1"}
        )
        lun_resource = self._make_local_resource("subscription_plugin", "Lun", lun_id="foobar", size=1024 * 1024)
        presentation_resource = self._make_local_resource(
            "subscription_plugin", "Presentation", host_id=self.host.id, path="/dev/foo", lun_id="foobar"
        )

        self.resource_manager.session_open(
            self.plugin, scannable_resource_pk, [scannable_resource, dev_resource, node_resource], 60
        )
        self.resource_manager.session_open(
            self.plugin, controller_record.pk, [controller_resource, lun_resource, presentation_resource], 60
        )

        lun_pk = self.resource_manager._sessions[controller_record.pk].local_id_to_global_id[lun_resource._handle]

        from chroma_core.services.plugin_runner.resource_manager import SubscriberIndex

        index = SubscriberIndex()
        index.populate()

        self.assertEqual(index.what_provides(presentation_resource), set([lun_pk]))
