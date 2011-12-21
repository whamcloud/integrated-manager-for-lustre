
from tests.configure.helper import JobTestCase

from configure.models.host import ManagedHost, Lun, LunNode


class TestHostAddRemove(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def test_creation(self):
        ManagedHost.create_from_string('myaddress')
        self.assertEqual(ManagedHost.objects.count(), 1)

    def test_dupe_creation(self):
        """ManagedHost.create_from_string is to ignore
        subsequent creation attempts for the same address"""
        ManagedHost.create_from_string('myaddress')
        ManagedHost.create_from_string('myaddress')
        self.assertEqual(ManagedHost.objects.count(), 1)

    def test_removal(self):
        host = ManagedHost.create_from_string('myaddress')

        self._test_lun(host)
        self.assertEqual(Lun.objects.count(), 1)
        self.assertEqual(LunNode.objects.count(), 1)

        from configure.lib.state_manager import StateManager
        StateManager.set_state(host, 'removed')
        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')
        self.assertEqual(ManagedHost.objects.count(), 0)
        self.assertEqual(Lun.objects.count(), 1)
        self.assertEqual(LunNode.objects.count(), 0)
