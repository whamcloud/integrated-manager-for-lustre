import json
import os
from chroma_core.models.host import ManagedHost, Volume, VolumeNode

from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins
from tests.unit.chroma_core.helper import JobTestCase


class LinuxPluginTestCase(JobTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp"]
        },
        'myaddress2': {
            'fqdn': 'myaddress2.mycompany.com',
            'nodename': 'test02.myaddress.mycompany.com',
            'nids': ["192.168.0.2@tcp"]
        }
    }

    def setUp(self):
        super(LinuxPluginTestCase, self).setUp()

        self.manager = load_plugins(['linux'])

        import chroma_core.lib.storage_plugin.manager
        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager

        import chroma_core.lib.storage_plugin.resource_manager
        self.old_resource_manager = chroma_core.lib.storage_plugin.resource_manager.resource_manager
        chroma_core.lib.storage_plugin.resource_manager.resource_manager = chroma_core.lib.storage_plugin.resource_manager.ResourceManager()

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager

        import chroma_core.lib.storage_plugin.resource_manager
        chroma_core.lib.storage_plugin.resource_manager.resource_manager = self.old_resource_manager

        super(LinuxPluginTestCase, self).tearDown()

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

        instance = plugin_klass(resource_record.id)
        instance.do_agent_session_start(data['linux'])

    def test_HYD_1269(self):
        """This test vector caused an exception during Volume generation.
        It has two block devices with the same serial_80, which should be
        caught where we scrub out the non-unique IDs that QEMU puts into
        serial_80."""
        host, command = ManagedHost.create_from_string('myaddress')
        self._start_session_with_data(host, "HYD_1269.json")
        self.assertEqual(Volume.objects.count(), 2)

    def test_HYD_1269_noerror(self):
        """This test vector is from a different machine at the same time which did not experience the HYD-1272 bug"""
        host, command = ManagedHost.create_from_string('myaddress')
        self._start_session_with_data(host, "HYD_1269_noerror.json")
        # Multiple partitioned devices, sda->sde, 2 partitions each
        # sda1 is boot, sda2 is a PV

        self.assertEqual(Volume.objects.count(), 8)
        self.assertEqual(VolumeNode.objects.count(), 8)

    def test_multipath(self):
        """Two hosts, each seeing two block devices via two nodes per block device,
        with multipath devices configured correctly"""
        host1, command = ManagedHost.create_from_string('myaddress')
        host2, command = ManagedHost.create_from_string('myaddress2')
        self._start_session_with_data(host1, "multipath.json")
        self._start_session_with_data(host2, "multipath.json")

        self.assertEqual(Volume.objects.count(), 2)
        self.assertEqual(VolumeNode.objects.count(), 4)

    def test_multipath_bare(self):
        """Two hosts, each seeing two block devices via two nodes per block device,
        with no multipath configuration"""
        host1, command = ManagedHost.create_from_string('myaddress')
        host2, command = ManagedHost.create_from_string('myaddress2')
        self._start_session_with_data(host1, "multipath_bare.json")
        self._start_session_with_data(host2, "multipath_bare.json")

        self.assertEqual(Volume.objects.count(), 2)
        self.assertEqual(VolumeNode.objects.count(), 8)

    def test_multipath_partitions_HYD_1385(self):
        """A single host, which sees a two-path multipath device that has partitions on it"""
        host1, command = ManagedHost.create_from_string('myaddress')
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
        host1, command = ManagedHost.create_from_string('myaddress')

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
        host1, command = ManagedHost.create_from_string('myaddress')
        self._start_session_with_data(host1, "HYD-1385_mounted.json")

        # The mounted partition should not be reported as an available volume
        with self.assertRaises(Volume.DoesNotExist):
            Volume.objects.get(label = "MPATH-testdev00-1")

        # The other partition should still be shown
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)
