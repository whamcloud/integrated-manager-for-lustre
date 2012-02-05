
from django.test import TestCase
from helper import load_plugins


class TestCornerCases(TestCase):
    def test_0classes(self):
        with self.assertRaisesRegexp(RuntimeError, "Module unloadable_plugin_0classes does not define a StoragePlugin"):
            load_plugins(['unloadable_plugin_0classes'])

    def test_2classes(self):
        with self.assertRaisesRegexp(RuntimeError, "Module unloadable_plugin_2classes defines more than one StoragePlugin"):
            load_plugins(['unloadable_plugin_2classes'])

    def test_dupemodule(self):
        with self.assertRaisesRegexp(RuntimeError, "Duplicate storage plugin module loadable_plugin"):
            load_plugins(['loadable_plugin', 'loadable_plugin'])

    def test_submodule(self):
        # Check we can load a plugin via a dotted reference
        mgr = load_plugins(['submodule.loadable_submodule_plugin'])
        # Check that the path has been stripped from the reference
        mgr.get_plugin_class('loadable_submodule_plugin')


class TestExample(TestCase):
    def test_load(self):
        """Test that the example plugin used in documentation loads"""
        load_plugins(['example_plugin'])


class TestLoad(TestCase):
    def setUp(self):
        import loadable_plugin
        self.loadable_plugin = loadable_plugin
        self.manager = load_plugins(['loadable_plugin'])

        import chroma_core
        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager

    def tearDown(self):
        import chroma_core
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager

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
        from chroma_core.models import StoragePluginRecord, StorageResourceClass, StorageResourceClassStatistic
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

    def test_get_resource_classes(self):
        """Test that the manager is correctly reporting classes and filtering ScannableResources"""
        # All the resources
        all_classes = self.manager.get_resource_classes()
        self.assertEqual(len(all_classes), 2)

        # Just the scannable resources
        scannable_classes = self.manager.get_resource_classes(scannable_only = True)
        self.assertEqual(len(scannable_classes), 1)
        scannable_classes = [sc.to_dict() for sc in scannable_classes]
        self.assertEqual(scannable_classes[0]['plugin_name'], 'loadable_plugin')
        self.assertEqual(scannable_classes[0]['class_name'], 'TestScannableResource')
        self.assertEqual(scannable_classes[0]['label'], 'loadable_plugin-TestScannableResource')

    def test_root_resource(self):
        """Test that the manager creates and returns a scannable resource"""
        record = self.manager.create_root_resource('loadable_plugin', 'TestScannableResource', name = 'foobar')
        self.assertEqual(self.manager.get_scannable_resource_ids('loadable_plugin'), [record.pk])
