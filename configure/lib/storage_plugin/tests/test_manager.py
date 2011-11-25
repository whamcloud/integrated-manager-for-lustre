
from django.utils import unittest
from helper import load_test_plugins


class TestCornerCases(unittest.TestCase):
    def test_0classes(self):
        with self.assertRaisesRegexp(RuntimeError, "Module unloadable_plugin_0classes does not define a StoragePlugin"):
            load_test_plugins(['unloadable_plugin_0classes'])

    def test_2classes(self):
        with self.assertRaisesRegexp(RuntimeError, "Module unloadable_plugin_2classes defines more than one StoragePlugin"):
            load_test_plugins(['unloadable_plugin_2classes'])

    def test_dupemodule(self):
        with self.assertRaisesRegexp(RuntimeError, "Duplicate storage plugin module loadable_plugin"):
            load_test_plugins(['loadable_plugin', 'loadable_plugin'])

    def test_submodule(self):
        # Check we can load a plugin via a dotted reference
        mgr = load_test_plugins(['submodule.loadable_submodule_plugin'])
        # Check that the path has been stripped from the reference
        mgr.get_plugin_class('loadable_submodule_plugin')


class TestLoad(unittest.TestCase):
    def setUp(self):
        import loadable_plugin
        self.loadable_plugin = loadable_plugin
        self.manager = load_test_plugins(['loadable_plugin'])

    def test_load(self):
        """Test that the manager correctly loaded and introspected
        the compoments of 'loadable_plugin'"""
        self.assertIn('loadable_plugin', self.manager.loaded_plugins)

        # Check these don't throw an exception
        self.manager.get_plugin_resource_class('loadable_plugin', 'TestScannableResource')
        self.manager.get_plugin_resource_class('loadable_plugin', 'TestResource')
        self.manager.get_plugin_class('loadable_plugin')

        # Explicitly check the list of all resources
        all_resources = self.manager.get_all_resources()
        all_resource_classes = [a[1].__name__ for a in all_resources]
        self.assertSetEqual(set(all_resource_classes), set(['TestResource', 'TestScannableResource']))

        # Check we populated the database elements for plugin, resources, and statistics
        from configure.models import StoragePluginRecord, StorageResourceClass, StorageResourceClassStatistic
        plugin = StoragePluginRecord.objects.get(module_name = 'loadable_plugin')
        resource = StorageResourceClass.objects.get(storage_plugin = plugin, class_name = 'TestResource')
        self.assertEqual(self.manager.get_resource_class_by_id(resource.pk).__name__, 'TestResource')
        StorageResourceClassStatistic.objects.get(resource_class = resource, name = 'thing_count')
        resource = StorageResourceClass.objects.get(storage_plugin = plugin, class_name = 'TestScannableResource')
        self.assertEqual(self.manager.get_resource_class_by_id(resource.pk).__name__, 'TestScannableResource')

    def test_absences(self):
        with self.assertRaises(RuntimeError):
            self.manager.get_plugin_resource_class('loadable_plugin', 'noexist')
        with self.assertRaises(RuntimeError):
            self.manager.get_plugin_resource_class('noexist', 'TestResource')

    def test_scannables(self):
        """Test that the manager is correctly reporting ScannableResources"""
        scannable_classes = self.manager.get_scannable_resource_classes()
        self.assertIn({'plugin': 'loadable_plugin', 'resource_class': 'TestScannableResource'}, scannable_classes)

    def test_root_resource(self):
        """Test that the manager creates and returns a scannable resource"""
        pk = self.manager.create_root_resource('loadable_plugin', 'TestScannableResource', name = 'foobar')
        self.assertEqual(self.manager.get_scannable_resource_ids('loadable_plugin'), [pk])
