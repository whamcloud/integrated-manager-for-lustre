from mock import patch

import unittest
from chroma_agent.plugin_manager import DevicePluginManager, ActionPluginManager
from chroma_agent.lib.agent_teardown_functions import agent_daemon_teardown_functions
from chroma_agent.lib.agent_startup_functions import agent_daemon_startup_functions
from chroma_agent.action_plugins.device_plugin import (
    initialise_block_device_drivers,
    terminate_block_device_drivers,
)


class TestDevicePlugins(unittest.TestCase):
    def test_get_device_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(DevicePluginManager.get_plugins()), 0)

    def test_excluded_plugins(self):
        self.assertTrue("linux" in DevicePluginManager.get_plugins())

        with patch("chroma_agent.plugin_manager.EXCLUDED_PLUGINS", ["linux"]):
            with patch.object(DevicePluginManager, "_plugins", {}):
                self.assertTrue("linux" not in DevicePluginManager.get_plugins())

    def test_initialise_block_device_drivers_called_at_startup(self):
        """Test method is added to list of functions to run on daemon startup."""
        self.assertTrue(initialise_block_device_drivers in agent_daemon_startup_functions)

    def test_terminate_block_device_drivers_called_at_teardown(self):
        """Test method is added to list of functions to run on daemon teardown."""
        self.assertTrue(terminate_block_device_drivers in agent_daemon_teardown_functions)


class TestActionPlugins(unittest.TestCase):
    def test_get_action_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(ActionPluginManager().commands), 0)
