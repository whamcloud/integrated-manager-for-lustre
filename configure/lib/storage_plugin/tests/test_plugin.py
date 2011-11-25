
#from django.utils import unittest
from django.test import TestCase
from configure.lib.storage_plugin.plugin import StoragePlugin
from configure.lib.storage_plugin.resource import StorageResource
from configure.lib.storage_plugin import attributes
from configure.lib.storage_plugin.resource import GlobalId, ScannableResource


class MockResourceManager(object):
    def __init__(self, *args, **kwargs):
        self.session_open_called = False
        super(MockResourceManager, self).__init__(*args, **kwargs)

    def session_open(self, scannable_id, scannable_local_id, initial_resources, update_period):
        self.session_open_called = True


class TestResource(StorageResource, ScannableResource):
    name = attributes.String()
    identifier = GlobalId('name')


class TestPlugin(StoragePlugin):
    _resource_classes = [TestResource]

    def __init__(self, *args, **kwargs):
        self.initial_scan_called = False
        self.update_scan_called = False
        self.teardown_called = False
        super(TestPlugin, self).__init__(*args, **kwargs)

    def initial_scan(self, root_resource):
        self.initial_scan_called = True

    def update_scan(self, root_resource):
        self.update_scan_called = True

    def teardown(self):
        self.teardown_called = True


class TestRegistration(TestCase):
    def test_registration(self):
        instance = TestPlugin()
        from configure.lib.storage_plugin.manager import storage_plugin_manager
        self.assertEqual(storage_plugin_manager.plugin_sessions[instance._handle], instance)


class TestCallbacks(TestCase):
    def test_initial(self):
        from configure.models import StorageResourceRecord
        for record in StorageResourceRecord.objects.all():
            print "zzz %s" % record

        from configure.lib.storage_plugin.manager import storage_plugin_manager
        storage_plugin_manager._load_plugin('test_mod', TestPlugin)
        storage_plugin_manager.create_root_resource('test_mod', 'TestResource', name = 'test1')

        from configure.lib.storage_plugin.query import ResourceQuery
        #from configure.models import StorageResourceRecord
        scannable_record = StorageResourceRecord.objects.get()
        scannable_resource = ResourceQuery().get_resource(scannable_record)
        scannable_global_id = scannable_record.pk

        instance = TestPlugin(scannable_global_id)

        import configure.lib.storage_plugin.resource_manager
        mrm = MockResourceManager()
        configure.lib.storage_plugin.resource_manager.resource_manager = mrm

        instance.do_initial_scan(scannable_resource)
        self.assertEquals(instance.initial_scan_called, True)
        self.assertEquals(mrm.session_open_called, True)
