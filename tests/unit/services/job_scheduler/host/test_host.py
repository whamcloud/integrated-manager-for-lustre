from copy import deepcopy
from itertools import chain
from mock import call, MagicMock, patch
import json

from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_api.urls import api
from tests.unit.chroma_core.helpers import MockAgentRpc
from tests.unit.chroma_core.helpers import synthetic_host, synthetic_volume_full
from chroma_core.models.host import ManagedHost, Volume, VolumeNode
from chroma_core.models.lnet_configuration import Nid
from tests.unit.services.job_scheduler.job_test_case import JobTestCase


class NidTestCase(JobTestCase):
    def setUp(self):
        super(NidTestCase, self).setUp()
        self.default_mock_servers = deepcopy(self.mock_servers)

    def tearDown(self):
        self.mock_servers = self.default_mock_servers
        super(NidTestCase, self).tearDown()

    def assertNidsCorrect(self, host):
        JobSchedulerClient.command_run_jobs(
            [{"class_name": "UpdateDevicesJob", "args": {"host_ids": json.dumps([host.id])}}], "Test update of nids"
        )
        self.drain_progress()

        mock_nids = set(
            [str(Nid.nid_tuple_to_string(Nid.Nid(n[0], n[1], n[2]))) for n in self.mock_servers[host.address]["nids"]]
        )
        recorded_nids = set([str(n.nid_string) for n in Nid.objects.filter(lnet_configuration__host=host)])

        self.assertSetEqual(mock_nids, recorded_nids)


class TestNidChange(NidTestCase):
    mock_servers = {
        "myaddress": {
            "fqdn": "myaddress.mycompany.com",
            "nodename": "test01.myaddress.mycompany.com",
            "nids": [Nid.Nid("192.168.0.1", "tcp", 0)],
        }
    }

    def attempt_nid_change(self, new_nids):
        host = synthetic_host("myaddress", self.mock_servers["myaddress"]["nids"])
        self.assertNidsCorrect(host)
        self.mock_servers["myaddress"]["nids"] = new_nids
        self.assertNidsCorrect(host)

    def test_relearn_change(self):
        self.attempt_nid_change([Nid.Nid("192.168.0.2", "tcp", 0)])

    def test_relearn_add(self):
        self.attempt_nid_change([Nid.Nid("192.168.0.1", "tcp", 0), Nid.Nid("192.168.0.2", "tcp", 0)])

    def test_relearn_remove(self):
        self.attempt_nid_change([])


class TestUpdateNids(NidTestCase):
    mock_servers = {
        "mgs": {
            "fqdn": "mgs.mycompany.com",
            "nodename": "mgs.mycompany.com",
            "nids": [Nid.Nid("192.168.0.1", "tcp", 0)],
        },
        "mds": {
            "fqdn": "mds.mycompany.com",
            "nodename": "mds.mycompany.com",
            "nids": [Nid.Nid("192.168.0.2", "tcp", 0)],
        },
        "oss": {
            "fqdn": "oss.mycompany.com",
            "nodename": "oss.mycompany.com",
            "nids": [Nid.Nid("192.168.0.3", "tcp", 0)],
        },
    }

    @patch("chroma_core.lib.job.Step.invoke_rust_agent", return_value=MagicMock())
    def test_mgs_nid_change(self, invoke):
        invoke.return_value = '{"Ok": ""}'

        mgs = synthetic_host("mgs")
        mds = synthetic_host("mds")
        oss = synthetic_host("oss")

        from chroma_core.models import (
            ManagedMgs,
            ManagedMdt,
            ManagedOst,
            ManagedFilesystem,
            ManagedTarget,
        )

        self.mgt, mgt_tms = ManagedMgs.create_for_volume(synthetic_volume_full(mgs).id, name="MGS")
        self.fs = ManagedFilesystem.objects.create(mgs=self.mgt, name="testfs")
        ObjectCache.add(ManagedFilesystem, self.fs)
        self.mdt, mdt_tms = ManagedMdt.create_for_volume(synthetic_volume_full(mds).id, filesystem=self.fs)
        self.ost, ost_tms = ManagedOst.create_for_volume(synthetic_volume_full(oss).id, filesystem=self.fs)
        for target in [self.mgt, self.ost, self.mdt]:
            ObjectCache.add(ManagedTarget, target.managedtarget_ptr)

        self.fs = self.set_and_assert_state(self.fs, "available")

        self.mock_servers["mgs"]["nids"] = [Nid.Nid("192.168.0.99", "tcp", 0)]
        self.assertNidsCorrect(mgs)

        JobSchedulerClient.command_run_jobs(
            [{"class_name": "UpdateNidsJob", "args": {"host_ids": json.dumps([mgs.id])}}], "Test update nids"
        )
        self.drain_progress()
        self.assertState(self.fs, "stopped")

        expected_calls = [
            call(
                "mgs",
                "lctl",
                ["replace_nids", "%s" % self.mdt, "192.168.0.2@tcp0"],
            ),
            call(
                "mgs",
                "lctl",
                ["replace_nids", "%s" % self.ost, "192.168.0.3@tcp0"],
            ),
        ]

        self.assertEqual(expected_calls, invoke.call_args_list)


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
        self.create_simple_filesystem(host)
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
