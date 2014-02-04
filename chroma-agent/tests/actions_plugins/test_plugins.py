from mock import patch

from django.utils.unittest import TestCase
from chroma_agent.plugin_manager import DevicePluginManager, ActionPluginManager


class TestDevicePlugins(TestCase):
    def test_get_device_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(DevicePluginManager.get_plugins()), 0)

    def test_excluded_plugins(self):
        self.assertTrue('linux' in DevicePluginManager.get_plugins())

        with patch('chroma_agent.plugin_manager.EXCLUDED_PLUGINS', ['linux']):
            with patch.object(DevicePluginManager, '_plugins', {}):
                self.assertTrue('linux' not in DevicePluginManager.get_plugins())


class TestActionPlugins(TestCase):
    def test_get_action_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(ActionPluginManager().commands), 0)
