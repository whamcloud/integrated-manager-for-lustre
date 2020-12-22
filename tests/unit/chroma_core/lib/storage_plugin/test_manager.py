import os

from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.management.commands.validate_storage_plugin import Command as ValidateCommand
import settings
import shutil


class TestCornerCases(IMLUnitTestCase):
    def test_0classes(self):
        manager = load_plugins(["unloadable_plugin_0classes"])
        self.assertEqual(manager.get_errored_plugins(), ["unloadable_plugin_0classes"])

    def test_2classes(self):
        manager = load_plugins(["unloadable_plugin_2classes"])
        self.assertEqual(manager.get_errored_plugins(), ["unloadable_plugin_2classes"])

    def test_dupemodule(self):
        manager = load_plugins(["loadable_plugin", "loadable_plugin"])
        self.assertEqual(manager.get_errored_plugins(), ["loadable_plugin"])

    def test_submodule(self):
        # Check we can load a plugin via a dotted reference
        mgr = load_plugins(["submodule.loadable_submodule_plugin"])
        self.assertEquals(mgr.get_errored_plugins(), [])
        # Check that the path has been stripped from the reference
        mgr.get_plugin_class("loadable_submodule_plugin")


class TestExample(IMLUnitTestCase):
    def test_load(self):
        """Test that the example plugin used in documentation loads"""
        manager = load_plugins(["linux", "example_plugin"])
        self.assertEquals(manager.get_errored_plugins(), [])


class TestThousandDrives(IMLUnitTestCase):
    def test_load(self):
        """Test that the thousand_drives plugin used for stats load testing loads"""
        manager = load_plugins(["thousand_drives"])
        self.assertEquals(manager.get_errored_plugins(), [])


class TestLoad(IMLUnitTestCase):
    def setUp(self):
        super(TestLoad, self).setUp()

        import loadable_plugin

        self.loadable_plugin = loadable_plugin
        self.manager = load_plugins(["loadable_plugin"])
        self.assertEquals(self.manager.get_errored_plugins(), [])

        import chroma_core

        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager

    def tearDown(self):
        import chroma_core

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager

    def test_load(self):
        """Test that the manager correctly loaded and introspected
        the compoments of 'loadable_plugin'"""
        self.assertIn("loadable_plugin", self.manager.loaded_plugins)

        # Check these don't throw an exception
        self.manager.get_plugin_resource_class("loadable_plugin", "TestScannableResource")
        self.manager.get_plugin_resource_class("loadable_plugin", "TestResource")
        self.manager.get_plugin_class("loadable_plugin")

        # Explicitly check the list of all resources
        all_resources = self.manager.get_all_resources()
        all_resource_classes = [a[1].__name__ for a in all_resources]
        self.assertSetEqual(set(all_resource_classes), set(["TestResource", "TestScannableResource"]))

        # Check we populated the database elements for plugin and resources
        from chroma_core.models import StoragePluginRecord, StorageResourceClass

        plugin = StoragePluginRecord.objects.get(module_name="loadable_plugin")
        resource = StorageResourceClass.objects.get(storage_plugin=plugin, class_name="TestResource")
        self.assertEqual(self.manager.get_resource_class_by_id(resource.pk).__name__, "TestResource")
        resource = StorageResourceClass.objects.get(storage_plugin=plugin, class_name="TestScannableResource")
        self.assertEqual(self.manager.get_resource_class_by_id(resource.pk).__name__, "TestScannableResource")

    def test_absences(self):
        from chroma_core.lib.storage_plugin.manager import PluginNotFound

        with self.assertRaises(PluginNotFound):
            self.manager.get_plugin_resource_class("loadable_plugin", "noexist")
        with self.assertRaises(PluginNotFound):
            self.manager.get_plugin_resource_class("noexist", "TestResource")

    def test_get_resource_classes(self):
        """Test that the manager is correctly reporting classes and filtering ScannableResources"""
        # All the resources
        all_classes = self.manager.get_resource_classes()
        self.assertEqual(len(all_classes), 2)

        # Just the scannable resources
        scannable_classes = self.manager.get_resource_classes(scannable_only=True)
        self.assertEqual(len(scannable_classes), 1)
        self.assertEqual(scannable_classes[0].storage_plugin.module_name, "loadable_plugin")
        self.assertEqual(scannable_classes[0].class_name, "TestScannableResource")

    def test_root_resource(self):
        """Test that the manager creates and returns a scannable resource"""
        from chroma_core.models import StorageResourceRecord

        resource_class, resource_class_id = self.manager.get_plugin_resource_class(
            "loadable_plugin", "TestScannableResource"
        )
        record, created = StorageResourceRecord.get_or_create_root(
            resource_class, resource_class_id, {"name": "foobar"}
        )
        self.assertEqual(self.manager.get_scannable_resource_ids("loadable_plugin"), [record.pk])


class TestValidate(IMLUnitTestCase):
    def setUp(self):
        super(TestValidate, self).setUp()
        import chroma_core.lib.storage_plugin.manager

        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        self.old_INSTALLED_STORAGE_PLUGINS = settings.INSTALLED_STORAGE_PLUGINS
        settings.INSTALLED_STORAGE_PLUGINS = []
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager
        settings.INSTALLED_STORAGE_PLUGINS = self.old_INSTALLED_STORAGE_PLUGINS

    def test_submodule(self):
        errors = ValidateCommand().execute(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "submodule/loadable_submodule_plugin.py")
        )
        self.assertListEqual(errors, [])

    def test_failures(self):
        errors = ValidateCommand().execute(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "unloadable_plugin_0classes.py")
        )
        self.assertListEqual(errors, ["Module unloadable_plugin_0classes does not define a BaseStoragePlugin!"])
        errors = ValidateCommand().execute(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "unloadable_plugin_2classes.py")
        )
        self.assertListEqual(
            errors,
            [
                "Module unloadable_plugin_2classes defines more than one BaseStoragePlugin: [<class 'unloadable_plugin_2classes.TestPluginOne'>, <class 'unloadable_plugin_2classes.TestPluginTwo'>]!"
            ],
        )
        errors = ValidateCommand().execute(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "unloadable_plugin_alerts_clash.py")
        )
        self.assertListEqual(
            errors,
            [
                "Resource class 'Controller': Multiple AlertConditions on the same attribute must be disambiguated with 'id' parameters."
            ],
        )

    def test_fake_controller(self):
        dirname = os.path.dirname(__file__) + "/../../../../plugins/"
        errors = ValidateCommand().execute(os.path.join(os.path.abspath(dirname), "fake_controller.py"))
        self.assertListEqual(errors, [])

    def test_thousand_drives(self):
        errors = ValidateCommand().execute(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "thousand_drives.py")
        )
        self.assertListEqual(errors, [])

    def test_junk(self):
        src = os.path.join(os.path.abspath(os.path.dirname(__file__)), "junk.not-really-py")
        dst = os.path.join(os.path.abspath(os.path.dirname(__file__)), "junk.py")
        shutil.copy(src, dst)
        errors = ValidateCommand().execute(dst)
        os.remove(dst)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("SyntaxError:"), errors[0])
