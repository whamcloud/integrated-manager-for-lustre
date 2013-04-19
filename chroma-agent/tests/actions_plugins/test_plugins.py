
from django.utils.unittest import TestCase
from chroma_agent.plugin_manager import DevicePluginManager, ActionPluginManager


class TestDevicePlugins(TestCase):
    def test_get_device_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(DevicePluginManager.get_plugins()), 0)


class TestActionPlugins(TestCase):
    def test_get_action_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(ActionPluginManager().commands), 0)
