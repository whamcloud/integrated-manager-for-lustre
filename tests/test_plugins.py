from django.utils import unittest
from hydra_agent import plugins


class TestPlugins(unittest.TestCase):
    def test_scan_plugins(self):
        """Test that we get a list of plugin names."""
        self.assertNotEqual(plugins.scan_plugins(), [])

    @unittest.skip("test not implemented")
    def test_load_plugins(self):
        """Test that plugins get imported."""
        pass

    def test_find_plugins(self):
        """Test that we get a list of loaded plugin instances."""
        self.assertNotEqual(plugins.find_plugins(), [])
