from chroma_core.models.host import Volume, VolumeNode
from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestResourceOperations(ResourceManagerTestCase):
    def setUp(self):
        super(TestResourceOperations, self).setUp("linux")

        resource_record, scannable_resource = self._make_global_resource(
            "linux", "PluginAgentResources", {"plugin_name": "linux", "host_id": self.host.id}
        )

        self.scannable_resource_pk = resource_record.pk
        self.scannable_resource = scannable_resource

        self.dev_resource = self._make_local_resource("linux", "ScsiDevice", serial="foobar", size=4096)
        self.node_resource = self._make_local_resource(
            "linux", "LinuxDeviceNode", path="/dev/foo", parents=[self.dev_resource], host_id=self.host.id
        )

    def test_re_add(self):
        self.resource_manager.session_open(
            self.plugin,
            self.scannable_resource_pk,
            [self.scannable_resource, self.dev_resource, self.node_resource],
            60,
        )

        self.assertEqual(StorageResourceRecord.objects.count(), 3)
        self.resource_manager.session_remove_local_resources(self.scannable_resource_pk, [self.node_resource])
        self.assertEqual(StorageResourceRecord.objects.count(), 2)
        self.resource_manager.session_add_resources(self.scannable_resource_pk, [self.node_resource])
        self.assertEqual(StorageResourceRecord.objects.count(), 3)

    def test_global_remove(self):
        self.resource_manager.session_open(
            self.plugin,
            self.scannable_resource_pk,
            [self.scannable_resource, self.dev_resource, self.node_resource],
            60,
        )
        self.assertEqual(StorageResourceRecord.objects.count(), 3)
        self.resource_manager.global_remove_resource(self.scannable_resource_pk)
        self.assertEqual(StorageResourceRecord.objects.count(), 0)

    def test_reference(self):
        """Create and save a resource which uses attributes.ResourceReference"""
        partition = self._make_local_resource(
            "linux", "Partition", container=self.dev_resource, number=0, size=1024 * 1024 * 500
        )

        self.resource_manager.session_open(
            self.plugin,
            self.scannable_resource_pk,
            [self.scannable_resource, partition, self.dev_resource, self.node_resource],
            60,
        )

        from chroma_core.models import StorageResourceAttributeReference

        self.assertEqual(StorageResourceAttributeReference.objects.count(), 1)
        self.assertNotEqual(StorageResourceAttributeReference.objects.get().value, None)

    def test_subscriber(self):
        """Create a pair of resources where one subscribes to the other"""
        controller_record, controller_resource = self._make_global_resource(
            "subscription_plugin", "Controller", {"address": "192.168.0.1"}
        )
        lun_resource = self._make_local_resource("subscription_plugin", "Lun", lun_id="foobar", size=1024 * 1024)
        presentation_resource = self._make_local_resource(
            "subscription_plugin", "Presentation", host_id=self.host.id, path="/dev/foo", lun_id="foobar"
        )

        # Session for host resources
        self.resource_manager.session_open(
            self.plugin,
            self.scannable_resource_pk,
            [self.scannable_resource, self.dev_resource, self.node_resource],
            60,
        )

        # Session for controller resources
        self.resource_manager.session_open(
            self.plugin, controller_record.pk, [controller_resource, lun_resource, presentation_resource], 60
        )

        # Check relations created
        node_klass, node_klass_id = self.manager.get_plugin_resource_class("linux", "LinuxDeviceNode")
        presentation_klass, presentation_klass_id = self.manager.get_plugin_resource_class(
            "subscription_plugin", "Presentation"
        )
        lun_klass, lun_klass_id = self.manager.get_plugin_resource_class("subscription_plugin", "Lun")
        records = StorageResourceRecord.objects.all()
        for r in records:
            resource = r.to_resource()
            parent_resources = [pr.to_resource().__class__ for pr in r.parents.all()]

            if isinstance(resource, node_klass):
                self.assertIn(presentation_klass, parent_resources)

            if isinstance(resource, presentation_klass):
                self.assertIn(lun_klass, parent_resources)

        count_before = StorageResourceRecord.objects.count()
        self.resource_manager.session_remove_local_resources(controller_record.pk, [presentation_resource])
        count_after = StorageResourceRecord.objects.count()

        self.assertEqual(StorageResourceRecord.objects.filter(resource_class=presentation_klass_id).count(), 0)

        # Check the Lun and DeviceNode are still there but the Presentation is gone
        self.assertEquals(count_after, count_before - 1)

    def test_update_host_lun_order1(self):
        """
        Test that Volumes are generated from LogicalDrives when they are reported
        in an update rather than the initial resource set, adding device before node
        resource and removing the device before the node resource
        """
        self._test_update_host_lun([self.dev_resource, self.node_resource], [self.dev_resource, self.node_resource])

    def test_update_host_lun_order2(self):
        """
        Test that Volumes are generated from LogicalDrives when they are reported
        in an update rather than the initial resource set, adding node before device
        resource and removing the device before the node resource
        """
        self._test_update_host_lun([self.node_resource, self.dev_resource], [self.dev_resource, self.node_resource])

    def test_update_host_lun_order3(self):
        """
        Test that Volumes are generated from LogicalDrives when they are reported
        in an update rather than the initial resource set, adding node before device
        resource and removing the node before the device resource
        """
        self._test_update_host_lun([self.node_resource, self.dev_resource], [self.node_resource, self.dev_resource])

    def test_update_host_lun_order4(self):
        """
        Test that Volumes are generated from LogicalDrives when they are reported
        in an update rather than the initial resource set, adding device before node
        resource and removing the node before the device resource
        """
        self._test_update_host_lun([self.dev_resource, self.node_resource], [self.node_resource, self.dev_resource])

    def _test_update_host_lun(self, addition_order, removal_order):
        self.resource_manager.session_open(self.plugin, self.scannable_resource_pk, [self.scannable_resource], 60)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)
        self.resource_manager.session_add_resources(self.scannable_resource_pk, addition_order)
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)
        self.resource_manager.session_remove_local_resources(self.scannable_resource_pk, removal_order)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_initial_host_lun(self):
        child_node_resource = self._make_local_resource(
            "linux", "LinuxDeviceNode", path="/dev/foobar", parents=[self.node_resource], host_id=self.host.id
        )

        self.resource_manager.session_open(
            self.plugin,
            self.scannable_resource_pk,
            [self.scannable_resource, self.dev_resource, self.node_resource, child_node_resource],
            60,
        )

        # Check we got a Volume and a VolumeNode
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)
        self.assertEqual(Volume.objects.get().label, self.dev_resource.get_label())

        # Check the VolumeNode got the correct path
        self.assertEqual(VolumeNode.objects.get().path, "/dev/foobar")
        self.assertEqual(VolumeNode.objects.get().host, self.host)

        # Check the created Volume has a link back to the UnsharedDevice
        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.models import StorageResourceRecord

        resource_record = StorageResourceRecord.objects.get(pk=self.scannable_resource_pk)
        dev_record = ResourceQuery().get_record_by_attributes("linux", "ScsiDevice", serial="foobar")

        self.assertEqual(Volume.objects.get().storage_resource_id, dev_record.pk)
        self.assertEqual(Volume.objects.get().size, 4096)

        # Try closing and re-opening the session, this time without the resources, the Volume/VolumeNode objects
        # should be removed
        self.resource_manager.session_close(resource_record.pk)

        self.resource_manager.session_open(self.plugin, resource_record.pk, [self.scannable_resource], 60)

        self.assertEqual(VolumeNode.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)

        # TODO: try again, but after creating some targets, check that the Volume/VolumeNode objects are NOT removed

        # TODO: try removing resources in an update_scan and check that Volume/VolumeNode are still removed

    def test_occupied_host_lun(self):
        """
        Test that when a ScsiDevice is reported with a filesystem on it, the resulting Volume
        is marked as occupied.
        """

        FILESYSTEM_TYPE = "ext2"
        occupied_dev_resource = self._make_local_resource(
            "linux", "ScsiDevice", serial="foobar", size=4096, filesystem_type=FILESYSTEM_TYPE
        )
        occupied_node_resource = self._make_local_resource(
            "linux", "LinuxDeviceNode", path="/dev/foo", parents=[occupied_dev_resource], host_id=self.host.id
        )

        self.resource_manager.session_open(
            self.plugin,
            self.scannable_resource_pk,
            [self.scannable_resource, occupied_dev_resource, occupied_node_resource],
            60,
        )

        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)
        self.assertEqual(Volume.objects.get().label, occupied_dev_resource.get_label())
        self.assertEqual(Volume.objects.get().filesystem_type, FILESYSTEM_TYPE)
