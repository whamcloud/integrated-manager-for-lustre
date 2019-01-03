from chroma_core.models.host import Volume, VolumeNode
from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestVolumeNaming(ResourceManagerTestCase):
    PLUGIN_LUN_NAME = "mylun123"
    SERIAL = "123abc456"
    VG = "foovg"
    LV = "foolv"

    def setUp(self):
        super(TestVolumeNaming, self).setUp("example_plugin")

    def _start_plugin_session(self):
        couplet_record, couplet_resource = self._make_global_resource(
            "example_plugin", "Couplet", {"address_1": "foo", "address_2": "bar"}
        )
        lun_resource = self._make_local_resource(
            "example_plugin", "Lun", local_id=1, name=self.PLUGIN_LUN_NAME, serial=self.SERIAL.upper(), size=4096
        )

        self.resource_manager.session_open(self.plugin, couplet_record.pk, [couplet_resource, lun_resource], 60)

    def _start_host_session(self, lvm=False, partition=False):
        host_record, host_resource = self._make_global_resource(
            "linux", "PluginAgentResources", {"plugin_name": "linux", "host_id": self.host.id}
        )

        dev_resource = self._make_local_resource("linux", "ScsiDevice", serial=self.SERIAL, size=4096)
        node_resource = self._make_local_resource(
            "linux",
            "LinuxDeviceNode",
            path="/dev/foo",
            parents=[dev_resource],
            host_id=self.host.id,
            logical_drive=dev_resource,
        )

        resources = [host_resource, dev_resource, node_resource]
        if lvm:
            vg_resource = self._make_local_resource(
                "linux",
                "LvmGroup",
                parents=[node_resource],
                name=self.VG,
                uuid="b44f7d8e-a40d-4b96-b241-2ab462b4c1c1",
                size=4096,
            )
            lv_resource = self._make_local_resource(
                "linux",
                "LvmVolume",
                parents=[vg_resource],
                name=self.LV,
                vg=vg_resource,
                uuid="b44f7d8e-a40d-4b96-b241-2ab462b4c1c1",
                size=4096,
            )
            lv_node_resource = self._make_local_resource(
                "linux",
                "LinuxDeviceNode",
                parents=[lv_resource],
                path="/dev/mapper/%s-%s" % (self.VG, self.LV),
                host_id=self.host.id,
            )
            resources.extend([vg_resource, lv_resource, lv_node_resource])

        if partition:
            partition_resource = self._make_local_resource(
                "linux", "Partition", number=1, container=dev_resource, size=20000, parents=[node_resource]
            )
            partition_node_resource = self._make_local_resource(
                "linux", "LinuxDeviceNode", parents=[partition_resource], path="/dev/foo1", host_id=self.host.id
            )
            resources.extend([partition_resource, partition_node_resource])

        self.resource_manager.session_open(self.plugin, host_record.pk, resources, 60)

    def assertVolumeName(self, name):
        """For simple single-volume tests, check the name of the volume"""
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)
        self.assertEqual(Volume.objects.get().label, name)

    def test_name_from_scsi(self):
        """In the absence of a plugin-supplied LUN, name should come from SCSI ID"""
        self._start_host_session()
        self.assertVolumeName(self.SERIAL)

    def test_name_from_partition(self):
        self._start_host_session(partition=True)

        # Partition is named as its ancestor LogicalDrive with a -N suffix
        partition_label = "%s-1" % self.SERIAL

        partition_obj = StorageResourceRecord.objects.get(
            resource_class_id=self.manager.get_plugin_resource_class("linux", "Partition")[1]
        )
        self.assertEqual(partition_label, partition_obj.to_resource().get_label())
        self.assertVolumeName(partition_label)

    def test_name_from_plugin_host_first(self):
        """When a plugin supplies a LUN which hooks up via SCSI ID, name should come from the LUN,
        in the harder case where the Volume has been created first and must be updated
        when the plugin resources are added.

        """

        self._start_host_session()
        self._start_plugin_session()
        self.assertVolumeName(self.PLUGIN_LUN_NAME)

    def test_name_from_plugin_host_second(self):
        """When a plugin supplies a LUN which hooks up via SCSI ID, name should come from the LUN,
        in the easier case where the plugin LUN already exists at Volume creation.

        """

        self._start_plugin_session()
        self._start_host_session()
        self.assertVolumeName(self.PLUGIN_LUN_NAME)

    def test_name_from_lvm(self):
        """When a volume corresponds to an LV, the name should come from LVM (not plugin-supplied
        LUN name, even if it's present."""
        self._start_plugin_session()
        self._start_host_session(lvm=True)
        self.assertVolumeName("%s-%s" % (self.VG, self.LV))
