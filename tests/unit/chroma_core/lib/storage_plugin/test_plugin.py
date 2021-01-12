import types
import sys

import mock

from chroma_core.services.plugin_runner.resource_manager import PluginSession
from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase
from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api import identifiers
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin


class TestLocalResource(resources.ScannableResource):
    class Meta:
        identifier = identifiers.ScopedId("name")

    name = attributes.String()


class TestGlobalResource(resources.ScannableResource):
    class Meta:
        identifier = identifiers.GlobalId("name")

    name = attributes.String()


class TestResourceExtraInfo(resources.ScannableResource):
    class Meta:
        identifier = identifiers.GlobalId("name")

    name = attributes.String()
    extra_info = attributes.String()


class TestResourceStatistic(resources.ScannableResource):
    class Meta:
        identifier = identifiers.GlobalId("name")

    name = attributes.String()
    extra_info = attributes.String()


class TestPlugin(Plugin):
    _resource_classes = [TestGlobalResource, TestLocalResource, TestResourceExtraInfo, TestResourceStatistic]

    def __init__(self, *args, **kwargs):
        self.initial_scan_called = False
        self.update_scan_called = False
        self.teardown_called = False

        Plugin.__init__(self, *args, **kwargs)

    def initial_scan(self, root_resource):
        self.initial_scan_called = True

    def update_scan(self, root_resource):
        self.update_scan_called = True

    def teardown(self):
        self.teardown_called = True


class TestCallbacks(EMFUnitTestCase):
    def setUp(self):
        super(TestCallbacks, self).setUp()

        import chroma_core.lib.storage_plugin.manager

        self.orig_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        storage_plugin_manager._load_plugin(sys.modules[__name__], "test_mod", TestPlugin)

        from chroma_core.models import StorageResourceRecord

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
            "test_mod", "TestGlobalResource"
        )
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {"name": "test1"})

        from chroma_core.lib.storage_plugin.query import ResourceQuery

        scannable_record = StorageResourceRecord.objects.get()
        self.scannable_resource = ResourceQuery().get_resource(scannable_record)
        self.scannable_global_id = scannable_record.pk

        self.resource_manager = mock.Mock(_sessions={})
        self.plugin = TestPlugin(self.resource_manager, self.scannable_global_id)
        self.resource_manager._sessions[self.scannable_global_id] = PluginSession(
            self.plugin, self.scannable_global_id, 0
        )

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.orig_manager

    def test_initial(self):
        self.plugin.initial_scan = mock.Mock()
        self.plugin.do_initial_scan()
        self.plugin.initial_scan.assert_called_once()

    def test_update(self):
        self.plugin.do_initial_scan()

        self.plugin.update_scan = mock.Mock()
        self.plugin.do_periodic_update()
        self.plugin.update_scan.assert_called_once()

    def test_teardown(self):
        self.plugin.do_initial_scan()

        self.plugin.teardown = mock.Mock()
        self.plugin.do_teardown()
        self.plugin.teardown.assert_called_once()


class TestAddRemove(EMFUnitTestCase):
    def setUp(self):
        super(TestAddRemove, self).setUp()

        import chroma_core.lib.storage_plugin.manager

        self.orig_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        storage_plugin_manager._load_plugin(sys.modules[__name__], "test_mod", TestPlugin)

        from chroma_core.models import StorageResourceRecord

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
            "test_mod", "TestGlobalResource"
        )
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {"name": "test1"})

        from chroma_core.lib.storage_plugin.query import ResourceQuery

        scannable_record = StorageResourceRecord.objects.get()
        self.scannable_resource = ResourceQuery().get_resource(scannable_record)
        self.scannable_global_id = scannable_record.pk

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.orig_manager

    def _report_resource(self, resource_to_report):
        def _report_a_resource(self, root_resource):
            if resource_to_report is not None:
                self.resource1, _ = self.update_or_create(resource_to_report, name="resource")

        return _report_a_resource

    def _remove_resource(self, resource_to_remove):
        def _remove_a_resource(self, root_resource):
            if resource_to_remove is not None:
                self.remove(resource_to_remove)

        return _remove_a_resource

    def _create_mocked_resource_and_plugin(self):
        self.resource_manager = mock.Mock(_sessions={})
        self.plugin = TestPlugin(self.resource_manager, self.scannable_global_id)
        self.resource_manager._sessions[self.scannable_global_id] = PluginSession(
            self.plugin, self.scannable_global_id, 0
        )

    def test_initial_resources(self):

        # First session for the scannable, 1 resource present
        self._create_mocked_resource_and_plugin()

        self.plugin.initial_scan = types.MethodType(self._report_resource(TestGlobalResource), self.plugin)

        # Should pass the scannable resource and the one we created to session_open
        self.plugin.do_initial_scan()
        self.resource_manager.session_open.assert_called_once_with(
            self.plugin,
            self.plugin._scannable_id,
            [self.plugin._root_resource, self.plugin.resource1],
            self.plugin._update_period,
        )

        # Session reporting 0 resource in initial_scan
        self._create_mocked_resource_and_plugin()

        self.plugin.initial_scan = types.MethodType(self._report_resource(None), self.plugin)
        self.plugin.do_initial_scan()

        # Should just report back the scannable resource to session_open
        self.resource_manager.session_open.assert_called_once_with(
            self.plugin, self.plugin._scannable_id, [self.plugin._root_resource], self.plugin._update_period
        )

    def test_update_add(self):
        self._create_mocked_resource_and_plugin()

        self.plugin.do_initial_scan()

        # Patch in an update_scan which reports one resource
        self.plugin.update_scan = types.MethodType(self._report_resource(TestGlobalResource), self.plugin)

        # Check that doing an update_or_create calls session_add_resources
        self.plugin.do_periodic_update()
        self.resource_manager.session_add_resources.assert_called_once_with(
            self.plugin._scannable_id, [self.plugin.resource1]
        )

        self.resource_manager.session_add_resources.reset_mock()

        # Check that doing a second update_or_create silently does nothing
        self.plugin.do_periodic_update()
        self.assertFalse(self.resource_manager.session_add_resources.called)

    def test_update_remove_global(self):
        self._create_mocked_resource_and_plugin()
        self.plugin.do_initial_scan()

        self.plugin.update_scan = types.MethodType(self._report_resource(TestGlobalResource), self.plugin)

        self.plugin.do_periodic_update()
        self.resource_manager.session_add_resources.assert_called_once_with(
            self.plugin._scannable_id, [self.plugin.resource1]
        )

        self.plugin.update_scan = types.MethodType(self._remove_resource(self.plugin.resource1), self.plugin)

        self.plugin.do_periodic_update()
        self.resource_manager.session_remove_global_resources.assert_called_once_with(
            self.plugin._scannable_id, [self.plugin.resource1]
        )

    def test_update_remove_local(self):
        self._create_mocked_resource_and_plugin()
        self.plugin.do_initial_scan()

        self.plugin.update_scan = types.MethodType(self._report_resource(TestLocalResource), self.plugin)

        self.plugin.do_periodic_update()
        self.resource_manager.session_add_resources.assert_called_once_with(
            self.plugin._scannable_id, [self.plugin.resource1]
        )

        self.plugin.update_scan = types.MethodType(self._remove_resource(self.plugin.resource1), self.plugin)

        self.plugin.do_periodic_update()
        self.resource_manager.session_remove_local_resources.assert_called_once_with(
            self.plugin._scannable_id, [self.plugin.resource1]
        )

    def test_update_modify_parents(self):
        self._create_mocked_resource_and_plugin()
        self.plugin.do_initial_scan()

        # Insert two resources, both having no parents
        def report_unrelated(self, root_resource):
            self.resource1, created = self.update_or_create(TestLocalResource, name="test1")
            self.resource2, created = self.update_or_create(TestLocalResource, name="test2")
            self.resource3, created = self.update_or_create(TestLocalResource, name="test3")

        self.plugin.update_scan = types.MethodType(report_unrelated, self.plugin)
        self.plugin.do_periodic_update()

        # Create a parent relationship between them
        def add_parents(self, root_resource):
            self.resource1.add_parent(self.resource2)

        self.plugin.update_scan = types.MethodType(add_parents, self.plugin)
        self.plugin.do_periodic_update()
        self.resource_manager.session_resource_add_parent.assert_called_once_with(
            self.plugin._scannable_id, self.plugin.resource1._handle, self.plugin.resource2._handle
        )

        # Remove the relationship
        def remove_parents(self, root_resource):
            self.resource1.remove_parent(self.resource2)

        self.plugin.update_scan = types.MethodType(remove_parents, self.plugin)
        self.plugin.do_periodic_update()
        self.resource_manager.session_resource_remove_parent.assert_called_once_with(
            self.plugin._scannable_id, self.plugin.resource1._handle, self.plugin.resource2._handle
        )

    def test_update_modify_attributes(self):
        self._create_mocked_resource_and_plugin()
        self.plugin.do_initial_scan()

        # Insert two resources, both having no parents
        def report1(self, root_resource):
            self.resource, created = self.update_or_create(TestResourceExtraInfo, name="test1", extra_info="foo")

        self.plugin.update_scan = types.MethodType(report1, self.plugin)
        self.plugin.do_periodic_update()

        # Modify the extra_info attribute
        def modify(self, root_resource):
            self.resource.extra_info = "bar"

        self.plugin.update_scan = types.MethodType(modify, self.plugin)
        self.plugin.do_periodic_update()
        self.resource_manager.session_update_resource.assert_called_once_with(
            self.plugin._scannable_id, self.plugin.resource._handle, {"extra_info": "bar"}
        )
