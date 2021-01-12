import mock

from chroma_core.services.plugin_runner.resource_manager import ResourceManager
from chroma_core.models.host import ManagedHost
from chroma_core.models.lnet_configuration import LNetConfiguration
from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins
from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase
from chroma_core.services.plugin_runner import AgentPluginHandlerCollection


class ResourceManagerTestCase(EMFUnitTestCase):
    def setUp(self, plugin_name="linux"):
        plugins_to_load = [
            "example_plugin",
            "linux",
            "linux_network",
            "subscription_plugin",
            "virtual_machine_plugin",
            "alert_plugin",
        ]

        assert plugin_name in plugins_to_load

        super(ResourceManagerTestCase, self).setUp()

        self.host = self._create_host(
            fqdn="myaddress.mycompany.com", nodename="myaddress.mycompany.com", address="myaddress.mycompany.com"
        )

        self.manager = load_plugins(plugins_to_load)

        mock.patch("chroma_core.lib.storage_plugin.manager.storage_plugin_manager", self.manager).start()

        self.resource_manager = ResourceManager()

        # Mock out the plugin queue otherwise we get all sorts of issues in ci. We really shouldn't
        # need all that ampq stuff just for the unit tests.
        mock.patch("chroma_core.services.queue.AgentRxQueue").start()

        self.plugin = (
            AgentPluginHandlerCollection(self.resource_manager).handlers[plugin_name]._create_plugin_instance(self.host)
        )

        self.addCleanup(mock.patch.stopall)

    def _create_host(self, fqdn, nodename, address):
        host = ManagedHost.objects.create(fqdn=fqdn, nodename=nodename, address=address)

        LNetConfiguration.objects.create(host=host, state="lnet_down")

        return host

    def __init__(self, *args, **kwargs):
        self._handle_counter = 0
        super(ResourceManagerTestCase, self).__init__(*args, **kwargs)

    def _get_handle(self):
        self._handle_counter += 1
        return self._handle_counter

    def _make_local_resource(self, plugin_name, class_name, **kwargs):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        klass, klass_id = storage_plugin_manager.get_plugin_resource_class(plugin_name, class_name)
        resource = klass(**kwargs)
        resource.validate()
        resource._handle = self._get_handle()
        resource._handle_global = False

        return resource

    def _make_global_resource(self, plugin_name, class_name, attrs):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(plugin_name, class_name)
        resource_record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)
        resource = resource_record.to_resource()
        resource._handle = self._get_handle()
        resource._handle_global = False
        return resource_record, resource
