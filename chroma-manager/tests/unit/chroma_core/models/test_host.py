from django.db.utils import IntegrityError
from tests.unit.chroma_core.helper import JobTestCase, MockAgent

from chroma_core.models.host import ManagedHost, Volume, VolumeNode


class TestHostAddRemove(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nodename': 'test01.myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def test_creation(self):
        ManagedHost.create_from_string('myaddress')
        self.assertEqual(ManagedHost.objects.count(), 1)

    def test_dupe_creation(self):
        ManagedHost.create_from_string('myaddress')
        with self.assertRaises(IntegrityError):
            ManagedHost.create_from_string('myaddress')
        self.assertEqual(ManagedHost.objects.count(), 1)

    def test_removal(self):
        host, command = ManagedHost.create_from_string('myaddress')

        self._test_lun(host)
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        self.set_state(host, 'removed')
        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')
        self.assertEqual(ManagedHost.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_force_removal(self):
        """Test the mode of removal which should not rely on the host
           being accessible"""
        host, command = ManagedHost.create_from_string('myaddress')

        self._test_lun(host)
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        # The host disappears, never to be seen again
        MockAgent.succeed = False
        try:
            from chroma_core.tasks import command_run_jobs
            command_run_jobs.delay([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
        finally:
            MockAgent.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')

        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_force_removal_with_filesystem(self):
        """Test that when a filesystem depends on a host, the filesystem
        is deleted along with the host when doing a force remove"""

        host, command = ManagedHost.create_from_string('myaddress')

        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt = ManagedMgs.create_for_volume(self._test_lun(host).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt = ManagedMdt.create_for_volume(self._test_lun(host).id, filesystem = self.fs)
        self.ost = ManagedOst.create_for_volume(self._test_lun(host).id, filesystem = self.fs)
        self.set_state(self.fs, 'available')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')

        # The host disappears, never to be seen again
        MockAgent.succeed = False
        try:
            from chroma_core.tasks import command_run_jobs
            command_run_jobs.delay([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
        finally:
            MockAgent.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')

        self.assertEqual(ManagedMgs.objects.count(), 0)
        self.assertEqual(ManagedFilesystem.objects.count(), 0)
        self.assertEqual(ManagedOst.objects.count(), 0)
        self.assertEqual(ManagedMdt.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)
