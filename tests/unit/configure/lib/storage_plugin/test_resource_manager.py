
from django.test import TestCase
from helper import load_plugins
from tests.unit.configure.helper import JobTestCase


class TestSessions(TestCase):
    def setUp(self):
        self.manager = load_plugins(['example_plugin'])
        record = self.manager.create_root_resource('example_plugin', 'Couplet', address_1 = "192.168.0.1", address_2 = "192.168.0.2")
        self.scannable_resource_id = record.pk

        import configure.lib.storage_plugin.manager
        configure.lib.storage_plugin.manager.storage_plugin_manager = self.manager

        import configure.lib.storage_plugin.resource_manager
        configure.lib.storage_plugin.resource_manager.resource_manager = configure.lib.storage_plugin.resource_manager.ResourceManager()

    def test_open_close(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager
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
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        import configure.lib.storage_plugin.resource_manager
        configure.lib.storage_plugin.resource_manager.resource_manager = configure.lib.storage_plugin.resource_manager.ResourceManager()

        super(TestLuns, self).setUp()

    def test_initial_host_lun(self):
        def get_handle():
            get_handle.handle_counter += 1
            return get_handle.handle_counter
        get_handle.handle_counter = 0

        from configure.models import ManagedHost
        host = ManagedHost.create_from_string('myaddress')

        from configure.lib.storage_plugin.query import ResourceQuery
        resource_record = ResourceQuery().get_record_by_attributes('linux', 'HydraHostProxy', host_id = host.pk)

        # Simplest case: an UnsharedDevice
        scannable_resource = resource_record.to_resource()
        scannable_resource._handle = get_handle()
        scannable_resource._handle_global = False

        from configure.lib.storage_plugin.manager import storage_plugin_manager
        klass, klass_id = storage_plugin_manager.get_plugin_resource_class('linux', 'UnsharedDevice')
        dev_resource = klass(path = "/dev/foo", size = 4096)
        dev_resource.validate()
        dev_resource._handle = get_handle()
        dev_resource._handle_global = False

        klass, klass_id = storage_plugin_manager.get_plugin_resource_class('linux', 'UnsharedDeviceNode')
        node_resource = klass(path = "/dev/foo", parents = [dev_resource], host = scannable_resource)
        node_resource.validate()
        node_resource._handle = get_handle()
        node_resource._handle_global = False

        from configure.lib.storage_plugin.resource_manager import resource_manager
        resource_manager.session_open(resource_record.pk, scannable_resource._handle, [dev_resource, node_resource], 60)

        # TODO: check that in a hierarchy Lun/LunNodes are only created for the leaves

        from configure.models import Lun, LunNode
        # Check we got a Lun and a LunNode
        self.assertEqual(Lun.objects.count(), 1)
        self.assertEqual(LunNode.objects.count(), 1)

        # Check the LunNode got the correct path
        self.assertEqual(LunNode.objects.get().path, "/dev/foo")
        self.assertEqual(LunNode.objects.get().host, host)

        # Check the created Lun has a link back to the UnsharedDevice
        dev_record = ResourceQuery().get_scannable_id_record_by_attributes(resource_record, 'linux', 'UnsharedDevice', path = "/dev/foo")
        self.assertEqual(Lun.objects.get().storage_resource_id, dev_record.pk)
        self.assertEqual(Lun.objects.get().size, 4096)

        # Try closing and re-opening the session, this time without the resources, the Lun/LunNode objects
        # should be removed
        resource_manager.session_close(resource_record.pk)
        resource_manager.session_open(resource_record.pk, scannable_resource._handle, [], 60)
        self.assertEqual(LunNode.objects.count(), 0)
        self.assertEqual(Lun.objects.count(), 0)

        # TODO: try again, but after creating some targets, check that the Lun/LunNode objects are NOT removed

        # TODO: try removing resources in an update_scan and check that Lun/LunNode are still removed


class TestVirtualMachines(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        import configure.lib.storage_plugin.resource_manager
        configure.lib.storage_plugin.resource_manager.resource_manager = configure.lib.storage_plugin.resource_manager.ResourceManager()

        super(TestVirtualMachines, self).setUp()

    def test_host_creation(self):
        pass
        # TODO: check that ManagedHosts are created when VirtualMachines are reported

    def test_virtual_disk_correlation(self):
        pass
        # TODO: check that a host created from a virtual machine gets its
        # LunNodes marked as primary when VirtualDisks are marked as homed
        # on the same controller
