from chroma_core.lib.util import dbperf
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.models.host import ManagedHost
from chroma_core.models.jobs import Command
from chroma_core.models.target import ManagedMdt, ManagedMgs, ManagedOst
from tests.unit.chroma_core.helper import JobTestCaseWithHost, freshen, JobTestCase
from django.db import connection


class TestOneHost(JobTestCase):
    mock_servers = {
        'myaddress': {
            'fqdn': 'myaddress.mycompany.com',
            'nodename': 'test01.myaddress.mycompany.com',
            'nids': ["192.168.0.1@tcp"]
        }
    }

    def setUp(self):
        super(TestOneHost, self).setUp()
        connection.use_debug_cursor = True

    def tearDown(self):
        super(TestOneHost, self).tearDown()
        connection.use_debug_cursor = False

    def test_one_host(self):
        try:
            dbperf.enabled = True

            with dbperf("create_from_string"):
                host, command = ManagedHost.create_from_string('myaddress')
            with dbperf("set_state"):
                Command.set_state([(host, 'lnet_up'), (host.lnetconfiguration, 'nids_known')], "Setting up host", run = False)
            with dbperf("run_next"):
                from chroma_core.services.job_scheduler.job_scheduler import run_next
                run_next()
            self.assertState(host, 'lnet_up')
        finally:
            dbperf.enabled = False


class TestBigFilesystem(JobTestCase):
    mock_servers = {}

    def setUp(self):
        super(TestBigFilesystem, self).setUp()
        connection.use_debug_cursor = True

    def tearDown(self):
        super(TestBigFilesystem, self).tearDown()
        connection.use_debug_cursor = False

    def test_big_filesystem(self):
        OSS_COUNT = 4
        OST_COUNT = 32

        assert OST_COUNT % OSS_COUNT == 0

        for i, address in enumerate(["oss%d" % i for i in range(0, OSS_COUNT)] + ['mds0', 'mds1', 'mgs0', 'mgs1']):
            self.mock_servers[address] = {
                'fqdn': address,
                'nodename': address,
                'nids': ["192.168.0.%d@tcp0" % i]
            }

        with dbperf("object creation"):
            self.mgs0, command = ManagedHost.create_from_string('mgs0')
            self.mgs1, command = ManagedHost.create_from_string('mgs1')
            self.mds0, command = ManagedHost.create_from_string('mds0')
            self.mds1, command = ManagedHost.create_from_string('mds1')
            self.osss = {}
            for i in range(0, OSS_COUNT):
                oss, command = ManagedHost.create_from_string('oss%d' % i)
                self.osss[i] = oss

            self.mgt = ManagedMgs.create_for_volume(self._test_lun(self.mgs0, self.mgs1).id, name = "MGS")
            self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
            self.mdt = ManagedMdt.create_for_volume(self._test_lun(self.mds0, self.mds1).id, filesystem = self.fs)

            self.osts = {}
            for i in range(0, OST_COUNT):
                primary_oss_i = (i * OSS_COUNT) / OST_COUNT
                if primary_oss_i % 2 == 1:
                    secondary_oss_i = primary_oss_i - 1
                else:
                    secondary_oss_i = primary_oss_i + 1
                primary_oss = self.osss[primary_oss_i]
                secondary_oss = self.osss[secondary_oss_i]
                self.osts[i] = ManagedOst.create_for_volume(self._test_lun(primary_oss, secondary_oss).id, filesystem = self.fs)

        try:
            dbperf.enabled = True
            import cProfile
            with dbperf("set_state"):
                #cProfile.runctx("Command.set_state([(self.osts[0], 'mounted')], 'Unit test transition', run = False)", globals(), locals(), 'set_state.prof')
                cProfile.runctx("Command.set_state([(self.fs, 'available')], 'Unit test transition', run = False)", globals(), locals(), 'set_state.prof')

            with dbperf('run_next'):
                from chroma_core.services.job_scheduler.job_scheduler import run_next
                run_next()
        finally:
            dbperf.enabled = False

        self.assertEqual(freshen(self.fs).state, 'available')


class TestFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestFSTransitions, self).setUp()

        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt = ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)
        self.ost = ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unformatted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unformatted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unformatted')

        self.set_state(self.fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')

    def test_mgs_removal(self):
        """Test that removing an MGS takes the filesystems with it"""
        self.set_state(self.mgt, 'removed')
        self.assertEqual(ManagedFilesystem.objects.count(), 0)

    def test_fs_removal(self):
        """Test that removing a filesystem takes its targets with it"""
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem
        self.set_state(self.fs, 'removed')

        with self.assertRaises(ManagedMdt.DoesNotExist):
            ManagedMdt.objects.get(pk = self.mdt.pk)
        self.assertEqual(ManagedMdt._base_manager.get(pk = self.mdt.pk).state, 'removed')
        with self.assertRaises(ManagedOst.DoesNotExist):
            ManagedOst.objects.get(pk = self.ost.pk)
        self.assertEqual(ManagedOst._base_manager.get(pk = self.ost.pk).state, 'removed')
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk = self.fs.pk)

    def test_fs_removal_mgt_offline(self):
        """Test that removing a filesystem whose MGT is offline leaves the MGT offline at completion"""
        self.set_state(self.mgt, 'unmounted')
        self.set_state(self.fs, 'removed')
        self.assertState(self.mgt, 'unmounted')
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk = self.fs.pk)

    def test_fs_removal_mgt_online(self):
        """Test that removing a filesystem whose MGT is online leaves the MGT online at completion, but
        stops it in the course of the removal (for the debugfs-ing)"""
        self.set_state(self.mgt, 'mounted')
        with self.assertInvokes('stop-target --ha_label %s' % freshen(self.mgt).ha_label):
            self.set_state(self.fs, 'removed')
        self.assertState(self.mgt, 'mounted')
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk = self.fs.pk)

    def test_two_concurrent_removes(self):
        fs2 = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)
        ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)

        self.set_state(self.fs, 'available')
        self.set_state(fs2, 'available')

        self.set_state(self.fs, 'removed', check = False, run = False)
        self.set_state(fs2, 'removed', check = False, run = False)

        self.set_state_complete()

        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk = self.fs.pk)

        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk = fs2.pk)

    def test_target_stop(self):
        from chroma_core.models import ManagedMdt, ManagedFilesystem
        self.set_state(self.mdt, 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'unavailable')

    def test_target_start(self):
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem

        self.set_state(self.fs, 'stopped')
        self.set_state(self.mdt, 'mounted')

        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'stopped')

        self.set_state(self.ost, 'mounted')
        self.assertState(self.fs, 'available')

    def test_stop_start(self):
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem
        self.set_state(self.fs, 'stopped')

        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'stopped')

        self.set_state(self.fs, 'available')

        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')

    def test_ost_changes(self):
        self.set_state(self.fs, 'stopped')
        ost_new = ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)
        self.set_state(self.mgt, 'mounted')
        self.set_state(self.mdt, 'mounted')
        self.set_state(self.ost, 'mounted')
        self.set_state(ost_new, 'mounted')
        self.assertState(self.fs, 'available')

        self.set_state(ost_new, 'unmounted')
        self.assertState(self.fs, 'unavailable')
        self.set_state(ost_new, 'removed')
        self.assertState(self.fs, 'available')


class TestDetectedFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestDetectedFSTransitions, self).setUp()

        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt = ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)
        self.ost = ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unformatted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unformatted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unformatted')

        self.set_state(self.fs, 'available')

        for obj in [self.mgt, self.mdt, self.ost, self.fs]:
            obj = freshen(obj)
            obj.immutable_state = True
            obj.save()

    def test_remove(self):
        from chroma_core.models import ManagedMgs, ManagedFilesystem, ManagedMdt, ManagedOst

        self.set_state(self.mgt, 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            freshen(self.mgt)
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            freshen(self.fs)
        with self.assertRaises(ManagedMdt.DoesNotExist):
            freshen(self.mdt)
        with self.assertRaises(ManagedOst.DoesNotExist):
            freshen(self.ost)
