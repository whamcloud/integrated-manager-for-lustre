from copy import deepcopy
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

from tests.unit.chroma_core.helper import JobTestCase, MockAgent
from chroma_core.models.host import NoLNetInfo
from tests.unit.chroma_core.helper import freshen
from django.db.utils import IntegrityError
import django.utils.timezone
from chroma_core.models.host import ManagedHost, Volume, VolumeNode, Nid
from chroma_core.models.jobs import Command
import settings


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
            MockAgent.fail_globs = ['device-plugin --plugin=lustre']
            host, command = ManagedHost.create_from_string('myaddress')
        finally:
            MockAgent.fail_globs = []
        self.assertState(host, 'configured')
        self.assertState(host.lnetconfiguration, 'nids_unknown')
        now = django.utils.timezone.now()
        with self.assertRaises(NoLNetInfo):
            freshen(host).lnetconfiguration.get_nids()
        JobSchedulerClient.notify_state(freshen(host), now, 'lnet_up', ['configured'])
        self.assertState(host.lnetconfiguration, 'nids_known')
        freshen(host).lnetconfiguration.get_nids()

    def test_selinux_detection(self):
        """Test that a host with SELinux enabled fails setup."""
        MockAgent.selinux_enabled = True
        try:
            import time
            host, command = ManagedHost.create_from_string('myaddress')
            while not command.complete:
                time.sleep(1)
            self.assertTrue(command.errored)
            self.assertState(host, 'unconfigured')
        finally:
            MockAgent.selinux_enabled = False

    def test_version(self):
        """Test manager-agent version compatibility."""
        versions = settings.VERSION, MockAgent.version
        settings.VERSION, MockAgent.version = '2.0', '1.0'
        try:
            host, command = ManagedHost.create_from_string('myaddress')
            self.assertTrue(command.errored)
            self.assertState(host, 'unconfigured')
            settings.VERSION = '1.1'
            command = Command.set_state([(host, 'configured')])
            self.assertFalse(command.errored)
            self.assertNotEqual(freshen(host).state, 'unconfigured')
        finally:
            settings.VERSION, MockAgent.version = versions


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
        host, command = ManagedHost.create_from_string('myaddress')
        self.set_state(host.lnetconfiguration, 'nids_known')
        self.assertNidsCorrect(host)
        self.mock_servers['myaddress']['nids'] = new_nids
        from chroma_api.urls import api
        JobSchedulerClient.command_run_jobs([{'class_name': 'RelearnNidsJob', 'args': {'hosts': [api.get_resource_uri(host)]}}], "Test relearn nids")
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
        mgs, command = ManagedHost.create_from_string('mgs')
        mds, command = ManagedHost.create_from_string('mds')
        oss, command = ManagedHost.create_from_string('oss')

        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt = ManagedMgs.create_for_volume(self._test_lun(mgs).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt = ManagedMdt.create_for_volume(self._test_lun(mds).id, filesystem = self.fs)
        self.ost = ManagedOst.create_for_volume(self._test_lun(oss).id, filesystem = self.fs)
        self.set_state(self.fs, 'available')

        self.mock_servers['mgs']['nids'] = ['192.168.0.99@tcp0']
        from chroma_api.urls import api
        JobSchedulerClient.command_run_jobs([{'class_name': 'RelearnNidsJob', 'args': {'hosts': [api.get_resource_uri(mgs)]}}], "Test relearn nids")
        self.assertNidsCorrect(mgs)

        JobSchedulerClient.command_run_jobs([{'class_name': 'UpdateNidsJob', 'args': {'hosts': [api.get_resource_uri(mgs)]}}], "Test update nids")
        # The -3 looks past the start/stop that happens after writeconf
        self.assertEqual(MockAgent.host_calls[mgs][-3][0], "writeconf-target")
        self.assertEqual(MockAgent.host_calls[mds][-3][0], "writeconf-target")
        self.assertEqual(MockAgent.host_calls[oss][-3][0], "writeconf-target")
        self.assertState(self.fs, 'stopped')


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
            JobSchedulerClient.command_run_jobs([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
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
            JobSchedulerClient.command_run_jobs([{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host.id}}], "Test host force remove")
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
