
from django.test import TestCase
from helper import load_plugins
from tests.unit.chroma_core.helper import JobTestCase


class TestSessions(TestCase):
    def setUp(self):
        self.manager = load_plugins(['example_plugin'])

        from chroma_core.models import StorageResourceRecord
        resource_class, resource_class_id = self.manager.get_plugin_resource_class('example_plugin', 'Couplet')
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {
            'address_1': '192.168.0.1', 'address_2': '192.168.0.2'})

        self.scannable_resource_id = record.pk

        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager

        import chroma_core.lib.storage_plugin.resource_manager
        chroma_core.lib.storage_plugin.resource_manager.resource_manager = chroma_core.lib.storage_plugin.resource_manager.ResourceManager()

    def test_open_close(self):
        from chroma_core.lib.storage_plugin.resource_manager import resource_manager
        self.assertEqual(len(resource_manager._sessions), 0)

        # Pretend I'm a plugin, I'm going to assign a local ID to my scannable resource
        local_scannable_id = 1

        # Create a new session (clean slate)
        resource_manager.session_open(self.scannable_resource_id, local_scannable_id, [], 60)
        self.assertEqual(len(resource_manager._sessions), 1)

        # Create a new session (override previous)
        resource_manager.session_open(self.scannable_resource_id, local_scannable_id, [], 60)
        self.assertEqual(len(resource_manager._sessions), 1)

        # Close a session
        resource_manager.session_close(self.scannable_resource_id)
        self.assertEqual(len(resource_manager._sessions), 0)


class TestLuns(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nodename': 'test01.myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        import chroma_core.lib.storage_plugin.resource_manager
        chroma_core.lib.storage_plugin.resource_manager.resource_manager = chroma_core.lib.storage_plugin.resource_manager.ResourceManager()

        super(TestLuns, self).setUp()

    def test_initial_host_lun(self):
        def get_handle():
            get_handle.handle_counter += 1
            return get_handle.handle_counter
        get_handle.handle_counter = 0

        from chroma_core.models import ManagedHost
        host, command = ManagedHost.create_from_string('myaddress')

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.models import StorageResourceRecord
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
        resource_record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': 'linux', 'host_id': host.id})

        # Simplest case: an UnsharedDevice
        scannable_resource = resource_record.to_resource()
        scannable_resource._handle = get_handle()
        scannable_resource._handle_global = False

        klass, klass_id = storage_plugin_manager.get_plugin_resource_class('linux', 'UnsharedDevice')
        dev_resource = klass(path = "/dev/foo", size = 4096)
        dev_resource.validate()
        dev_resource._handle = get_handle()
        dev_resource._handle_global = False

        klass, klass_id = storage_plugin_manager.get_plugin_resource_class('linux', 'LinuxDeviceNode')
        node_resource = klass(path = "/dev/foo", parents = [dev_resource], host_id = host.id)
        node_resource.validate()
        node_resource._handle = get_handle()
        node_resource._handle_global = False

        from chroma_core.lib.storage_plugin.resource_manager import resource_manager
        resource_manager.session_open(resource_record.pk, scannable_resource._handle, [dev_resource, node_resource], 60)

        # TODO: check that in a hierarchy Volume/VolumeNodes are only created for the leaves

        from chroma_core.models import Volume, VolumeNode
        # Check we got a Volume and a VolumeNode
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        # Check the VolumeNode got the correct path
        self.assertEqual(VolumeNode.objects.get().path, "/dev/foo")
        self.assertEqual(VolumeNode.objects.get().host, host)

        # Check the created Volume has a link back to the UnsharedDevice
        from chroma_core.lib.storage_plugin.query import ResourceQuery
        dev_record = ResourceQuery().get_scannable_id_record_by_attributes(resource_record, 'linux', 'UnsharedDevice', path = "/dev/foo")
        self.assertEqual(Volume.objects.get().storage_resource_id, dev_record.pk)
        self.assertEqual(Volume.objects.get().size, 4096)

        # Try closing and re-opening the session, this time without the resources, the Volume/VolumeNode objects
        # should be removed
        resource_manager.session_close(resource_record.pk)
        resource_manager.session_open(resource_record.pk, scannable_resource._handle, [], 60)
        self.assertEqual(VolumeNode.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)

        # TODO: try again, but after creating some targets, check that the Volume/VolumeNode objects are NOT removed

        # TODO: try removing resources in an update_scan and check that Volume/VolumeNode are still removed


class TestVirtualMachines(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nodename': 'test01.myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        import chroma_core.lib.storage_plugin.resource_manager
        chroma_core.lib.storage_plugin.resource_manager.resource_manager = chroma_core.lib.storage_plugin.resource_manager.ResourceManager()

        super(TestVirtualMachines, self).setUp()

    def test_host_creation(self):
        pass
        # TODO: check that ManagedHosts are created when VirtualMachines are reported

    def test_virtual_disk_correlation(self):
        pass
        # TODO: check that a host created from a virtual machine gets its
        # VolumeNodes marked as primary when VirtualDisks are marked as homed
        # on the same controller
