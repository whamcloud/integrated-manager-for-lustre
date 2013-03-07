
from copy import deepcopy
from itertools import chain
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

from tests.unit.chroma_core.helper import MockAgentRpc, synthetic_host, synthetic_volume_full
from chroma_core.models.host import NoLNetInfo
from tests.unit.chroma_core.helper import freshen
import django.utils.timezone
from chroma_core.models.host import ManagedHost, Volume, VolumeNode, Nid
from tests.unit.services.job_scheduler.job_test_case import JobTestCase


class TestSetup(JobTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp"]
        }
    }

    def test_nid_learning(self):
        """Test that if a host is added and then acquired lnet_up state passively,
        we will go and get the NIDs"""
        try:
            MockAgentRpc.fail_commands = [('device_plugin', {'plugin': 'lustre'})]
            host = synthetic_host('myaddress')
        finally:
            MockAgentRpc.fail_commands = []

        self.assertState(host, 'configured')
        self.assertState(host.lnetconfiguration, 'nids_unknown')
        now = django.utils.timezone.now()
        with self.assertRaises(NoLNetInfo):
            freshen(host).lnetconfiguration.get_nids()
        JobSchedulerClient.notify(freshen(host), now, {'state': 'lnet_up'}, ['configured'])
        self.assertState(host.lnetconfiguration, 'nids_known')
        freshen(host).lnetconfiguration.get_nids()


class NidTestCase(JobTestCase):
    def setUp(self):
        super(NidTestCase, self).setUp()
        self.default_mock_servers = deepcopy(self.mock_servers)

    def tearDown(self):
        self.mock_servers = self.default_mock_servers
        super(NidTestCase, self).tearDown()

    def assertNidsCorrect(self, host):
        self.assertSetEqual(
            set([n.nid_string for n in Nid.objects.filter(lnet_configuration__host = host)]),
            set(self.mock_servers[host.address]['nids']))


class TestNidChange(NidTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp0"]
        }
    }

    def attempt_nid_change(self, new_nids):
        host = synthetic_host('myaddress', self.mock_servers['myaddress']['nids'])
        self.set_state(host.lnetconfiguration, 'nids_known')
        self.assertNidsCorrect(host)
        self.mock_servers['myaddress']['nids'] = new_nids
        from chroma_api.urls import api
        JobSchedulerClient.command_run_jobs([{'class_name': 'RelearnNidsJob', 'args': {'hosts': [api.get_resource_uri(host)]}}], "Test relearn nids")
        self.drain_progress()
        self.assertNidsCorrect(host)

    def test_relearn_change(self):
        self.attempt_nid_change(["192.168.0.2@tcp0"])

    def test_relearn_add(self):
        self.attempt_nid_change(["192.168.0.1@tcp0", "192.168.0.2@tcp0"])

    def test_relearn_remove(self):
        self.attempt_nid_change([])


class TestUpdateNids(NidTestCase):
    mock_servers = {
        'mgs': {
            'fqdn': 'mgs.mycompany.com',
            'nodename': 'mgs.mycompany.com',
            'nids': ["192.168.0.1@tcp0"]
        },
        'mds': {
            'fqdn': 'mds.mycompany.com',
            'nodename': 'mds.mycompany.com',
            'nids': ["192.168.0.2@tcp0"]
        },
        'oss': {
            'fqdn': 'oss.mycompany.com',
            'nodename': 'oss.mycompany.com',
            'nids': ["192.168.0.3@tcp0"]
        },
    }

    def test_mgs_nid_change(self):
        mgs = synthetic_host('mgs')
        mds = synthetic_host('mds')
        oss = synthetic_host('oss')

        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem, ManagedTarget, ManagedTargetMount
        self.mgt, mgt_tms = ManagedMgs.create_for_volume(synthetic_volume_full(mgs).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt, mdt_tms = ManagedMdt.create_for_volume(synthetic_volume_full(mds).id, filesystem = self.fs)
        self.ost, ost_tms = ManagedOst.create_for_volume(synthetic_volume_full(oss).id, filesystem = self.fs)
        ObjectCache.add(ManagedFilesystem, self.fs)
        for target in [self.mgt, self.ost, self.mdt]:
            ObjectCache.add(ManagedTarget, target.managedtarget_ptr)
        for tm in chain(mgt_tms, mdt_tms, ost_tms):
            ObjectCache.add(ManagedTargetMount, tm)

        self.set_state(self.fs, 'available')

        self.mock_servers['mgs']['nids'] = ['192.168.0.99@tcp0']
        from chroma_api.urls import api
        JobSchedulerClient.command_run_jobs([{'class_name': 'RelearnNidsJob', 'args': {'hosts': [api.get_resource_uri(mgs)]}}], "Test relearn nids")
        self.drain_progress()
        self.assertNidsCorrect(mgs)

        JobSchedulerClient.command_run_jobs([{'class_name': 'UpdateNidsJob', 'args': {'hosts': [api.get_resource_uri(mgs)]}}], "Test update nids")
        self.drain_progress()
        # The -3 looks past the start/stop that happens after writeconf
        self.assertEqual(MockAgentRpc.host_calls[mgs][-3][0], "writeconf_target")
        self.assertEqual(MockAgentRpc.host_calls[mds][-3][0], "writeconf_target")
        self.assertEqual(MockAgentRpc.host_calls[oss][-3][0], "writeconf_target")
        self.assertState(self.fs, 'stopped')


class TestHostAddRemove(JobTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp"]
        }
    }

    def test_removal(self):
        host = synthetic_host('myaddress')
        synthetic_volume_full(host)

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
        host = synthetic_host('myaddress')

        synthetic_volume_full(host)
        self.assertEqual(Volume.objects.count(), 1)
        self.assertEqual(VolumeNode.objects.count(), 1)

        # The host disappears, never to be seen again
        MockAgentRpc.succeed = False
        try:
            JobSchedulerClient.command_run_jobs([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
            self.drain_progress()
        finally:
            MockAgentRpc.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')

        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)

    def test_force_removal_with_filesystem(self):
        """Test that when a filesystem depends on a host, the filesystem
        is deleted along with the host when doing a force remove"""

        host = synthetic_host('myaddress')
        self.create_simple_filesystem(host)
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem

        self.set_state(self.fs, 'available')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')

        # The host disappears, never to be seen again
        MockAgentRpc.succeed = False
        try:
            JobSchedulerClient.command_run_jobs([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
            self.drain_progress()
        finally:
            MockAgentRpc.succeed = True

        with self.assertRaises(ManagedHost.DoesNotExist):
            ManagedHost.objects.get(address = 'myaddress')

        self.assertEqual(ManagedMgs.objects.count(), 0)
        self.assertEqual(ManagedFilesystem.objects.count(), 0)
        self.assertEqual(ManagedOst.objects.count(), 0)
        self.assertEqual(ManagedMdt.objects.count(), 0)
        self.assertEqual(Volume.objects.count(), 0)
        self.assertEqual(VolumeNode.objects.count(), 0)
