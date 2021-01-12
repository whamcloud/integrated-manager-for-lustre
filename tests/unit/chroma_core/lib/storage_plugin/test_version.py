import imp
import sys

from django.conf import settings

from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase


def make_plugin_module(version=None, name="test_plugin_name", extra_body=None):
    """Creates a plugin module with only the version field, optionally

    The module is added to sys.modules, and both the name and module returned.
    """

    #  Create a plugin encoded with a version
    plugin_module = imp.new_module(name)

    if version is not None:
        plugin_module_body = "version = %s" % version
    else:
        plugin_module_body = ""

    if extra_body is not None:
        plugin_module_body = "%s\n\n%s" % (plugin_module_body, extra_body)

    exec(plugin_module_body) in plugin_module.__dict__

    #  Simulate imported
    sys.modules[name] = plugin_module

    return name, plugin_module


class TestValidateApiVersion(EMFUnitTestCase):
    """Test StoragePluginManager._validate_api_version method"""

    def test_version_match(self):
        """Test that both the plugin and manager api match versions"""
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager as mgr

        name, mod = make_plugin_module(version=1)
        settings.STORAGE_API_VERSION = 1
        mgr._validate_api_version(mod)

    def test_loading_old_version(self):
        """Test that old versions of plugins aren't valid."""
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager as mgr
        from chroma_core.lib.storage_plugin.manager import VersionMismatchError

        name, mod = make_plugin_module(version=1)
        settings.STORAGE_API_VERSION = 2
        self.assertRaises(VersionMismatchError, mgr._validate_api_version, mod)

    def test_loading_newer_version(self):
        """Test that newer versions of plugins aren't valid."""
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager as mgr
        from chroma_core.lib.storage_plugin.manager import VersionMismatchError

        name, mod = make_plugin_module(version=2)
        settings.STORAGE_API_VERSION = 1
        self.assertRaises(VersionMismatchError, mgr._validate_api_version, mod)

    def test_version_not_found(self):
        """Test that plugins not delcaring a version aren't loaded."""
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager as mgr
        from chroma_core.lib.storage_plugin.manager import VersionNotFoundError

        name, mod = make_plugin_module(version=None)
        settings.STORAGE_API_VERSION = 1
        self.assertRaises(VersionNotFoundError, mgr._validate_api_version, mod)

    def test_version_without_value(self):
        """Test that plugins delaring version without a value don't load

        version =

        Is invalid Python which will not import, which happens before the
        module is validated.
        Leaving this here to say it was considered as a test
        """
        pass

    def test_version_with_non_int_value(self):
        """Delaring version without an int value is not allowed"""
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager as mgr
        from chroma_core.lib.storage_plugin.manager import VersionMismatchError

        for c in [1.2, '"version1"', [1, 2, 3], {"version": 1}]:
            name, mod = make_plugin_module(version=c)

            #  initialize manager to accept only version 1 plugins
            settings.STORAGE_API_VERSION = 1

        self.assertRaises(VersionMismatchError, mgr._validate_api_version, mod)


class TestValidatedModuleLoading(EMFUnitTestCase):
    """Test that version checking integrates from nearly the starting load

    This test assumes the job of importing the plugin, which is something
    the StoragePluginManager actually does.  Since importing is a
    prerequisite for version checking to work, I opted not to test cover that.

    If a plugin didn't import cleanly, it would fail out before the version
    check could take place.
    """

    def _load_plugin(self, name):
        from chroma_core.lib.storage_plugin.manager import StoragePluginManager

        orginal_plugins = sys.modules["settings"].INSTALLED_STORAGE_PLUGINS
        sys.modules["settings"].INSTALLED_STORAGE_PLUGINS = [name]
        self.manager = StoragePluginManager()
        sys.modules["settings"].INSTALLED_STORAGE_PLUGINS = orginal_plugins

    def test_version_matches(self):
        from chroma_core.lib.storage_plugin.manager import VersionMismatchError, VersionNotFoundError

        version_exceptions = (VersionNotFoundError, VersionMismatchError)
        name, mod = make_plugin_module(version=1)
        settings.STORAGE_API_VERSION = 1
        self._load_plugin(name)

        #  Since the test plugin is invalid for other reason, it will fail
        #  But not because of a version mismatch
        self.assertEqual(name, self.manager.errored_plugins[0][0])
        error_class = self.manager.errored_plugins[0][1].__class__
        self.assertTrue(error_class not in version_exceptions)

    def test_version_mismatch(self):
        from chroma_core.lib.storage_plugin.manager import VersionMismatchError

        name, mod = make_plugin_module(version=1)
        settings.STORAGE_API_VERSION = 2
        self._load_plugin(name)

        self.assertEqual(name, self.manager.errored_plugins[0][0])
        self.assertEqual(self.manager.errored_plugins[0][1].__class__, VersionMismatchError)

    def test_version_not_found(self):
        from chroma_core.lib.storage_plugin.manager import VersionNotFoundError

        name, mod = make_plugin_module(version=None)
        settings.STORAGE_API_VERSION = 1
        self._load_plugin(name)

        self.assertEqual(name, self.manager.errored_plugins[0][0])
        self.assertEqual(self.manager.errored_plugins[0][1].__class__, VersionNotFoundError)
