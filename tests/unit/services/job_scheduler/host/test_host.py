from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tests.unit.chroma_core.helpers.mock_agent_rpc import MockAgentRpc
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host, synthetic_volume_full
from chroma_core.models.host import ManagedHost, Volume, VolumeNode
from chroma_core.models.lnet_configuration import Nid
from tests.unit.services.job_scheduler.job_test_case import JobTestCase


class TestHostAddRemove(JobTestCase):
    mock_servers = {
        "myaddress": {
            "fqdn": "myaddress.mycompany.com",
            "nodename": "test01.myaddress.mycompany.com",
            "nids": [Nid.Nid("192.168.0.1", "tcp", 0)],
        }
    }

    def test_removal(self):
        host = synthetic_host("myaddress")
        synthetic_volume_full(host)

        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        host = self.set_and_assert_state(host, "removed")
        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address="myaddress")
        self.assertEqual(ManagedHost.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_force_removal(self):
        """Test the mode of removal which should not rely on the host
        being accessible"""
        host = synthetic_host("myaddress")

        synthetic_volume_full(host)
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        # The host disappears, never to be seen again
        MockAgentRpc.succeed = False
        try:
            JobSchedulerClient.command_run_jobs(
                [{"class_name": "ForceRemoveHostJob", "args": {"host_id": host.id}}], "Test host force remove"
            )
            self.drain_progress()
        finally:
            MockAgentRpc.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address="myaddress")

        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_force_removal_with_filesystem(self):
        """Test that when a filesystem depends on a host, the filesystem
        is deleted along with the host when doing a force remove"""

        host = synthetic_host("myaddress")
        self.create_simple_filesystem()
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem

        self.fs = self.set_and_assert_state(self.fs, "available")
        self.assertState(self.mgt.managedtarget_ptr, "mounted")
        self.assertState(self.mdt.managedtarget_ptr, "mounted")
        self.assertState(self.ost.managedtarget_ptr, "mounted")
        self.assertEqual(ManagedFilesystem.objects.get(pk=self.fs.pk).state, "available")

        # The host disappears, never to be seen again
        MockAgentRpc.succeed = False
        try:
            JobSchedulerClient.command_run_jobs(
                [{"class_name": "ForceRemoveHostJob", "args": {"host_id": host.id}}], "Test host force remove"
            )
            self.drain_progress()
        finally:
            MockAgentRpc.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address="myaddress")

        self.assertEqual(ManagedMgs.objects.count(), 0)
        self.assertEqual(ManagedOst.objects.count(), 0)
        self.assertEqual(ManagedMdt.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)
        self.assertEqual(ManagedFilesystem.objects.count(), 0)
