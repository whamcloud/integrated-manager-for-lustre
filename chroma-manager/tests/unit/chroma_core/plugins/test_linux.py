import json
from chroma_core.services.plugin_runner import ResourceManager
from django.test import TestCase
import os
from chroma_core.models.host import Volume, VolumeNode

from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.helper import synthetic_host
from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins


class LinuxPluginTestCase(TestCase):
    def setUp(self):
        self.manager = load_plugins(['linux'])

        import chroma_core.lib.storage_plugin.manager
        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager

        self.resource_manager = ResourceManager()

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager

    def __init__(self, *args, **kwargs):
        self._handle_counter = 0
        super(LinuxPluginTestCase, self).__init__(*args, **kwargs)

    def _make_global_resource(self, plugin_name, class_name, attrs):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(plugin_name, class_name)
        resource_record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)
        return resource_record

    def _start_session_with_data(self, host, data_file):
        # This test impersonates AgentDaemon (load and pass things into a plugin instance)

        plugin_klass = self.manager.get_plugin_class('linux')

        data = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures/%s" % data_file)))

        resource_record = self._make_global_resource('linux', 'PluginAgentResources',
                {'plugin_name': 'linux', 'host_id': host.id})

        instance = plugin_klass(self.resource_manager, resource_record.id)
        instance.do_agent_session_start(data['linux'])

    def test_HYD_1269(self):
        """This test vector caused an exception during Volume generation.
        It has two block devices with the same serial_80, which should be
        caught where we scrub out the non-unique IDs that QEMU puts into
        serial_80."""
        host = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host, "HYD_1269.json")
        self.assertEqual(Volume.objects.count(), 2)

    def test_HYD_1269_noerror(self):
        """This test vector is from a different machine at the same time which did not experience the HYD-1272 bug"""
        host = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host, "HYD_1269_noerror.json")
        # Multiple partitioned devices, sda->sde, 2 partitions each
        # sda1 is boot, sda2 is a PV

        self.assertEqual(Volume.objects.count(), 8)
        self.assertEqual(VolumeNode.objects.count(), 8)

    def test_multipath(self):
        """Two hosts, each seeing two block devices via two nodes per block device,
        with multipath devices configured correctly"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        host2 = synthetic_host('myaddress2', storage_resource=True)
        self._start_session_with_data(host1, "multipath.json")
        self._start_session_with_data(host2, "multipath.json")

        self.assertEqual(Volume.objects.count(), 2)
        self.assertEqual(VolumeNode.objects.count(), 4)

    def test_multipath_bare(self):
        """Two hosts, each seeing two block devices via two nodes per block device,
        with no multipath configuration"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        host2 = synthetic_host('myaddress2', storage_resource=True)
        self._start_session_with_data(host1, "multipath_bare.json")
        self._start_session_with_data(host2, "multipath_bare.json")

        self.assertEqual(Volume.objects.count(), 2)
        self.assertEqual(VolumeNode.objects.count(), 8)

    def test_multipath_partitions_HYD_1385(self):
        """A single host, which sees a two-path multipath device that has partitions on it"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host1, "HYD-1385.json")

        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)

        # And now try it again to make sure that the un-wanted VolumeNodes don't get created on the second pass
        self._start_session_with_data(host1, "HYD-1385.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)

    def test_multipath_partitions_HYD_1385_mpath_creation(self):
        """First load a view where there are two nodes that haven't been multipathed together, then
        update with the multipath device in place"""
        host1 = synthetic_host('myaddress', storage_resource=True)

        # There is no multipath
        self._start_session_with_data(host1, "HYD-1385_nompath.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 2)

        # ... now there is, the VolumeNodes should change to reflect that
        self._start_session_with_data(host1, "HYD-1385.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)

        # ... and now it's gone again, the VolumeNodes should change back
        self._start_session_with_data(host1, "HYD-1385_nompath.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 2)

    def test_multipath_partitions_HYD_1385_mounted(self):
        """A single host, which sees a two-path multipath device that has partitions on it, one of
        the partitions is mounted via its /dev/mapper/*p1 device node"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host1, "HYD-1385_mounted.json")

        # The mounted partition should not be reported as an available volume
        with self.assertRaises(Volume.DoesNotExist):
            Volume.objects.get(label = "MPATH-testdev00-1")

        # The other partition should still be shown
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)

    def test_HYD_1969(self):
        """Reproducer for HYD-1969, one shared volume is being reported as two separate volumes with the same label."""
        host1 = synthetic_host('mds00', storage_resource=True)
        host2 = synthetic_host('mds01', storage_resource=True)

        self._start_session_with_data(host1, "HYD-1969-mds00.json")
        self._start_session_with_data(host2, "HYD-1969-mds01.json")

        self.assertEqual(Volume.objects.filter(label="3690b11c00006c68d000007ea5158674f").count(), 1)
