
from django.test import TestCase
from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin

import mock
import types
import sys


class TestResource(resources.ScannableResource):
    class Meta:
        identifier = GlobalId('name')

    name = attributes.String()


class TestSecondResource(resources.ScannableResource):
    class Meta:
        identifier = GlobalId('name')

    name = attributes.String()


class TestResourceExtraInfo(resources.ScannableResource):
    class Meta:
        identifier = GlobalId('name')

    name = attributes.String()
    extra_info = attributes.String()


class TestResourceStatistic(resources.ScannableResource):
    class Meta:
        identifier = GlobalId('name')

    name = attributes.String()
    extra_info = attributes.String()


class TestPlugin(Plugin):
    _resource_classes = [TestResource,
                         TestSecondResource,
                         TestResourceExtraInfo,
                         TestResourceStatistic]

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


class TestCallbacks(TestCase):
    def setUp(self):
        import chroma_core.lib.storage_plugin.manager
        self.orig_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = chroma_core.lib.storage_plugin.manager.StoragePluginManager()

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        storage_plugin_manager._load_plugin(sys.modules[__name__], 'test_mod', TestPlugin)

        from chroma_core.models import StorageResourceRecord
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('test_mod', 'TestResource')
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'name': 'test1'})

        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.models import StorageResourceRecord
        scannable_record = StorageResourceRecord.objects.get()
        self.scannable_resource = ResourceQuery().get_resource(scannable_record)
        self.scannable_global_id = scannable_record.pk

        import chroma_core.lib.storage_plugin.resource_manager
        self.mrm = mock.Mock(spec_set=chroma_core.lib.storage_plugin.resource_manager.ResourceManager)
        self.orig_resource_manager = chroma_core.lib.storage_plugin.resource_manager.resource_manager
        chroma_core.lib.storage_plugin.resource_manager.resource_manager = self.mrm

    def tearDown(self):
        import chroma_core.lib.storage_plugin.resource_manager
        chroma_core.lib.storage_plugin.resource_manager.resource_manager = self.orig_resource_manager
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.orig_manager

    def test_initial(self):
        instance = TestPlugin(self.scannable_global_id)
        instance.initial_scan = mock.Mock()
        instance.do_initial_scan()
        instance.initial_scan.assert_called_once()

    def test_update(self):
        instance = TestPlugin(self.scannable_global_id)
        instance.do_initial_scan()

        instance.update_scan = mock.Mock()
        instance.do_periodic_update()
        instance.update_scan.assert_called_once()

    def test_teardown(self):
        instance = TestPlugin(self.scannable_global_id)
        instance.do_initial_scan()

        instance.teardown = mock.Mock()
        instance.do_teardown()
        instance.teardown.assert_called_once()


class TestAddRemove(TestCase):
    def setUp(self):
        import chroma_core.lib.storage_plugin.manager
        self.orig_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = chroma_core.lib.storage_plugin.manager.StoragePluginManager()

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        storage_plugin_manager._load_plugin(sys.modules[__name__], 'test_mod', TestPlugin)

        from chroma_core.models import StorageResourceRecord
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('test_mod', 'TestResource')
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'name': 'test1'})

        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.models import StorageResourceRecord
        scannable_record = StorageResourceRecord.objects.get()
        self.scannable_resource = ResourceQuery().get_resource(scannable_record)
        self.scannable_global_id = scannable_record.pk

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.orig_manager

    def test_initial_resources(self):
        def report1(self, root_resource):
            self.resource1, created = self.update_or_create(TestSecondResource, name = 'test1')

        def report0(self, root_resource):
            pass

        with mock.patch('chroma_core.lib.storage_plugin.resource_manager.resource_manager') as rm:
            # First session for the scannable, 1 resource present
            instance = TestPlugin(self.scannable_global_id)
            instance.initial_scan = types.MethodType(report1, instance)

            # Should pass the scannable resource and the one we created to session_open
            instance.do_initial_scan()
            rm.session_open.assert_called_once_with(
                    instance._scannable_id,
                    [instance._root_resource, instance.resource1],
                    instance.update_period)

        with mock.patch('chroma_core.lib.storage_plugin.resource_manager.resource_manager') as rm:
            # Session reporting 0 resource in initial_scan
            instance = TestPlugin(self.scannable_global_id)
            instance.initial_scan = types.MethodType(report0, instance)
            instance.do_initial_scan()

            # Should just report back the scannable resource to session_open
            rm.session_open.assert_called_once_with(
                    instance._scannable_id,
                    [instance._root_resource],
                    instance.update_period)

    def test_update_add(self):
        with mock.patch('chroma_core.lib.storage_plugin.resource_manager.resource_manager') as rm:
            instance = TestPlugin(self.scannable_global_id)
            instance.do_initial_scan()

            # Patch in an update_scan which reports one resource
            def report1(self, root_resource):
                self.resource1, created = self.update_or_create(TestSecondResource, name = 'test1')
            instance.update_scan = types.MethodType(report1, instance)

            # Check that doing an update_or_create calls session_add_resources
            instance.do_periodic_update()
            rm.session_add_resources.assert_called_once_with(instance._scannable_id, [instance.resource1])

            rm.session_add_resources.reset_mock()

            # Check that doing a second update_or_create silently does nothing
            instance.do_periodic_update()
            self.assertFalse(rm.session_add_resources.called)

    def test_update_remove(self):
        with mock.patch('chroma_core.lib.storage_plugin.resource_manager.resource_manager') as rm:
            instance = TestPlugin(self.scannable_global_id)
            instance.do_initial_scan()

            def report1(self, root_resource):
                self.resource1, created = self.update_or_create(TestSecondResource, name = 'test1')
            instance.update_scan = types.MethodType(report1, instance)

            instance.do_periodic_update()
            rm.session_add_resources.assert_called_once_with(instance._scannable_id, [instance.resource1])

            def remove1(self, root_resource):
                self.remove(self.resource1)
            instance.update_scan = types.MethodType(remove1, instance)

            instance.do_periodic_update()
            rm.session_remove_resources.assert_called_once_with(instance._scannable_id, [instance.resource1])

    def test_update_modify_parents(self):
        with mock.patch('chroma_core.lib.storage_plugin.resource_manager.resource_manager') as rm:
            instance = TestPlugin(self.scannable_global_id)
            instance.do_initial_scan()

            # Insert two resources, both having no parents
            def report_unrelated(self, root_resource):
                self.resource1, created = self.update_or_create(TestSecondResource, name = 'test1')
                self.resource2, created = self.update_or_create(TestSecondResource, name = 'test2')
                self.resource3, created = self.update_or_create(TestSecondResource, name = 'test3')
            instance.update_scan = types.MethodType(report_unrelated, instance)
            instance.do_periodic_update()

            # Create a parent relationship between them
            def add_parents(self, root_resource):
                self.resource1.add_parent(self.resource2)
            instance.update_scan = types.MethodType(add_parents, instance)
            instance.do_periodic_update()
            rm.session_resource_add_parent.assert_called_once_with(instance._scannable_id,
                                                                   instance.resource1._handle,
                                                                   instance.resource2._handle)

            # Remove the relationship
            def remove_parents(self, root_resource):
                self.resource1.remove_parent(self.resource2)
            instance.update_scan = types.MethodType(remove_parents, instance)
            instance.do_periodic_update()
            rm.session_resource_remove_parent.assert_called_once_with(instance._scannable_id,
                                                                      instance.resource1._handle,
                                                                      instance.resource2._handle)

    def test_update_modify_attributes(self):
        with mock.patch('chroma_core.lib.storage_plugin.resource_manager.resource_manager') as rm:
            instance = TestPlugin(self.scannable_global_id)
            instance.do_initial_scan()

            # Insert two resources, both having no parents
            def report1(self, root_resource):
                self.resource, created = self.update_or_create(TestResourceExtraInfo, name = 'test1', extra_info = 'foo')
            instance.update_scan = types.MethodType(report1, instance)
            instance.do_periodic_update()

            # Modify the extra_info attribute
            def modify(self, root_resource):
                self.resource.extra_info = 'bar'
            instance.update_scan = types.MethodType(modify, instance)
            instance.do_periodic_update()
            rm.session_update_resource.assert_called_once_with(instance._scannable_id,
                                                               instance.resource._handle,
                                                               {'extra_info': 'bar'})

    def test_update_statistics(self):
        pass
