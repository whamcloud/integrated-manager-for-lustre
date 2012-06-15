import json
import os

from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins
from tests.unit.chroma_core.helper import JobTestCaseWithHost


class LinuxPluginTestCase(JobTestCaseWithHost):
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

    def _start_session_with_data(self, data_file):
        # This test impersonates AgentDaemon (load and pass things into a plugin instance)

        plugin_klass = self.manager.get_plugin_class('linux')

        data = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures/%s" % data_file)))

        resource_record = self._make_global_resource('linux', 'PluginAgentResources',
                {'plugin_name': 'linux', 'host_id': self.host.id})

        instance = plugin_klass(resource_record.id)
        instance.do_agent_session_start(data['linux'])

    def test_HYD_1272(self):
        """This test vector caused an exception during Volume generation"""
        self._start_session_with_data("HYD_1269.json")

    def test_HYD_1272_noerror(self):
        """This test vector is from a different machine at the same time which did not experience the HYD-1272 bug"""
        self._start_session_with_data("HYD_1269_noerror.json")
