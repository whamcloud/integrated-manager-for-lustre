import os
from django.utils.unittest import TestCase
from chroma_agent.plugin_manager import DevicePluginManager, ActionPluginManager
from chroma_agent.action_plugins import manage_updates
from mock import patch
from tempfile import NamedTemporaryFile


class TestDevicePlugins(TestCase):
    def test_get_device_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(DevicePluginManager.get_plugins()), 0)


class TestActionPlugins(TestCase):
    def test_get_action_plugins(self):
        """Test that we get a list of loaded plugin classes."""
        self.assertNotEqual(len(ActionPluginManager().commands), 0)


class TestActionUpdatesPlugin(TestCase):
    def setUp(self):
        super(TestActionUpdatesPlugin, self).setUp()
        self.tmpRepo = NamedTemporaryFile(delete=False)

    def tearDown(self):
        if os.path.exists(self.tmpRepo.name):
            os.remove(self.tmpRepo.name)

    def test_configure_repo(self):
        expected_content = """
[Intel Lustre Manager]
name=Intel Lustre Manager updates
baseurl=http://www.test.com/test.repo
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = /var/lib/chroma/authority.crt
sslclientkey = /var/lib/chroma/private.pem
sslclientcert = /var/lib/chroma/self.crt
"""
        with patch('__builtin__.open', spec=file, create=True) as mock_open:
            with patch('chroma_agent.store.AgentStore.libdir', return_value="/var/lib/chroma/"):
                manage_updates.configure_repo('http://www.test.com/test.repo')
                mock_open.return_value.write.assert_called_once_with(expected_content)

    def test_unconfigure_repo(self):
        manage_updates.unconfigure_repo(self.tmpRepo.name)
        self.assertFalse(os.path.exists(self.tmpRepo.name))

    def test_update_packages(self):
        with patch('chroma_agent.shell.try_run') as mock_run:
            manage_updates.update_packages(self.tmpRepo.name)
            mock_run.assert_called_once_with(['yum', '-y', 'update'])

    def test_reboot(self):
        with patch('chroma_agent.shell.try_run') as mock_run:
            manage_updates.restart_server()
            mock_run.assert_called_once_with(['reboot'])
