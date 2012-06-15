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
