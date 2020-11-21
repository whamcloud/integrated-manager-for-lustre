from itertools import chain

from django.db import connection

from chroma_core.lib.cache import ObjectCache
from chroma_core.lib.util import dbperf
from chroma_core.models import ManagedFilesystem
from chroma_core.models import Nid
from chroma_core.models import ManagedMdt, ManagedMgs, ManagedOst, ManagedTarget
from tests.unit.chroma_core.helpers import freshen
from tests.unit.chroma_core.helpers import synthetic_host
from tests.unit.services.job_scheduler.job_test_case import JobTestCase, JobTestCaseWithHost


class TestOneHost(JobTestCase):
    mock_servers = {
        "myaddress": {
            "fqdn": "myaddress.mycompany.com",
            "nodename": "test01.myaddress.mycompany.com",
            "nids": [Nid.Nid("192.168.0.1", "tcp", 0)],
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
                host = synthetic_host("myaddress")
            with dbperf("set_state"):
                self.set_state_delayed([(host, "managed")])
            with dbperf("run_next"):
                self.set_state_complete()
            self.assertState(host, "managed")
        finally:
            dbperf.enabled = False


class TestBigFilesystem(JobTestCase):
    """
    This test is a utility for use in tuning/optimisation: vary the object counts to see how
    our query count scales with it (not a correctness test)
    """

    mock_servers = {}

    def setUp(self):
        super(TestBigFilesystem, self).setUp()
        connection.use_debug_cursor = True

    def tearDown(self):
        super(TestBigFilesystem, self).tearDown()
        connection.use_debug_cursor = False

    # def test_big_filesystem(self):
    #     OSS_COUNT = 2
    #     OST_COUNT = 4
    #
    #     assert OST_COUNT % OSS_COUNT == 0
    #
    #     for i, address in enumerate(["oss%d" % i for i in range(0, OSS_COUNT)] + ['mds0', 'mds1', 'mgs0', 'mgs1']):
    #         self.mock_servers[address] = {
    #             'fqdn': address,
    #             'nodename': address,
    #             'nids': [Nid.Nid("192.168.0.%d" % i, "tcp", 0)]
    #         }
    #
    #     with dbperf("object creation"):
    #         self.mgs0 = self._synthetic_host_with_nids('mgs0')
    #         self.mgs1 = self._synthetic_host_with_nids('mgs1')
    #         self.mds0 = self._synthetic_host_with_nids('mds0')
    #         self.mds1 = self._synthetic_host_with_nids('mds1')
    #         self.osss = {}
    #         for i in range(0, OSS_COUNT):
    #             self.osss[i] = self._synthetic_host_with_nids('oss%d' % i)
    #
    #         self.mgt, mgt_tms = ManagedMgs.create_for_volume(self._test_lun(self.mgs0, self.mgs1).id, name = "MGS")
    #         self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
    #         self.mdt, mdt_tms = ManagedMdt.create_for_volume(self._test_lun(self.mds0, self.mds1).id, filesystem = self.fs)
    #
    #         self.osts = {}
    #         ost_tms = []
    #         for i in range(0, OST_COUNT):
    #             primary_oss_i = (i * OSS_COUNT) / OST_COUNT
    #             if primary_oss_i % 2 == 1:
    #                 secondary_oss_i = primary_oss_i - 1
    #             else:
    #                 secondary_oss_i = primary_oss_i + 1
    #             primary_oss = self.osss[primary_oss_i]
    #             secondary_oss = self.osss[secondary_oss_i]
    #             self.osts[i], tms = ManagedOst.create_for_volume(self._test_lun(primary_oss, secondary_oss).id, filesystem = self.fs)
    #             ost_tms.extend(tms)
    #         ObjectCache.add(ManagedFilesystem, self.fs)
    #         for target in [self.mgt, self.mdt] + self.osts.values():
    #             ObjectCache.add(ManagedTarget, target.managedtarget_ptr)
    #         for tm in chain(mgt_tms, mdt_tms, ost_tms):
    #             ObjectCache.add(ManagedTargetMount, tm)
    #
    #     try:
    #         dbperf.enabled = True
    #         import cProfile
    #         total = dbperf('total')
    #         with total:
    #             with dbperf("set_state"):
    #                 cProfile.runctx("self.set_state_delayed([(self.fs, 'available')])", globals(), locals(), 'set_state.prof')
    #             with dbperf('run_next'):
    #                 self.job_scheduler._run_next()
    #     finally:
    #         dbperf.enabled = False
    #     self.assertState(self.fs, 'available')


class TestIncompleteSetup(JobTestCaseWithHost):
    def test_fs_removal_mgt_unformatted(self):
        """Test that removing a filesystem which was never formatted (and whose mgt was
        never formatted) works (needs to be smart enough to avoid trying to purge
        config logs from an unformatted mgs)

        """
        self.create_simple_filesystem(self.host, start=False)

        self.assertState(self.mgt, "unformatted")
        self.fs = self.set_and_assert_state(self.fs, "removed")
        self.assertState(self.mgt, "unformatted")
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk=self.fs.pk)


class TestFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestFSTransitions, self).setUp()

        self.create_simple_filesystem(self.host, start=False)
        self.assertEqual(self.mgt.state, "unformatted")
        self.assertEqual(self.mdt.state, "unformatted")
        self.assertEqual(self.ost.state, "unformatted")

        self.fs = self.set_and_assert_state(self.fs, "available")

        self.assertState(self.mgt, "mounted")
        self.assertState(self.mdt, "mounted")
        self.assertState(self.ost, "mounted")
        self.assertState(self.fs, "available")

    def test_fs_removal(self):
        """Test that removing a filesystem takes its targets with it"""
        self.fs = self.set_and_assert_state(self.fs, "removed")

        with self.assertRaises(ManagedMdt.DoesNotExist):
            ManagedMdt.objects.get(pk=self.mdt.pk)
        self.assertEqual(ManagedMdt._base_manager.get(pk=self.mdt.pk).state, "removed")
        with self.assertRaises(ManagedOst.DoesNotExist):
            ManagedOst.objects.get(pk=self.ost.pk)
        self.assertEqual(ManagedOst._base_manager.get(pk=self.ost.pk).state, "removed")
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk=self.fs.pk)

    def test_fs_removal_mgt_offline(self):
        """Test that removing a filesystem whose MGT is offline starts the MGT and can remove successfully"""
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "unmounted")
        self.fs = self.set_and_assert_state(self.fs, "removed")
        self.assertState(self.mgt.managedtarget_ptr, "mounted")
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk=self.fs.pk)

    def test_fs_removal_mgt_online(self):
        """Test removing a filesystem whose MGT is online."""
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "mounted")
        self.fs = self.set_and_assert_state(self.fs, "removed")
        self.assertState(self.mgt, "mounted")
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk=self.fs.pk)

    def test_two_concurrent_removes(self):
        """
        Test that we can concurrently remove two filesystems which depend on the same mgt
        """
        fs2 = ManagedFilesystem.objects.create(mgs=self.mgt, name="testfs2")
        ObjectCache.add(ManagedFilesystem, fs2)
        mdt2, mdt_tms = ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem=fs2)
        ost2, ost_tms = ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem=fs2)
        for target in [mdt2, ost2]:
            ObjectCache.add(ManagedTarget, target.managedtarget_ptr)

        self.fs = self.set_and_assert_state(self.fs, "available")
        fs2 = self.set_and_assert_state(fs2, "available")

        self.set_state_delayed([(self.fs, "removed")])
        self.set_state_delayed([(fs2, "removed")])

        self.set_state_complete()

        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk=self.fs.pk)

        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk=fs2.pk)

    def test_target_stop(self):
        from chroma_core.models import ManagedMdt, ManagedFilesystem

        self.mdt.managedtarget_ptr = self.set_and_assert_state(self.mdt.managedtarget_ptr, "unmounted")
        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "unmounted")
        self.assertEqual(ManagedFilesystem.objects.get(pk=self.fs.pk).state, "unavailable")

    def test_target_start(self):
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem

        self.fs = self.set_and_assert_state(self.fs, "stopped")
        self.mdt.managedtarget_ptr = self.set_and_assert_state(freshen(self.mdt.managedtarget_ptr), "mounted")

        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "mounted")
        self.assertEqual(ManagedOst.objects.get(pk=self.ost.pk).state, "unmounted")
        self.assertEqual(ManagedFilesystem.objects.get(pk=self.fs.pk).state, "stopped")

        self.ost.managedtarget_ptr = self.set_and_assert_state(freshen(self.ost.managedtarget_ptr), "mounted")
        self.assertState(self.fs, "available")

    def test_stop_start(self):
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem

        self.fs = self.set_and_assert_state(self.fs, "stopped")

        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "unmounted")
        self.assertEqual(ManagedOst.objects.get(pk=self.ost.pk).state, "unmounted")
        self.assertEqual(ManagedFilesystem.objects.get(pk=self.fs.pk).state, "stopped")

        self.fs = self.set_and_assert_state(self.fs, "available")

        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "mounted")
        self.assertEqual(ManagedOst.objects.get(pk=self.ost.pk).state, "mounted")
        self.assertEqual(ManagedFilesystem.objects.get(pk=self.fs.pk).state, "available")

    def test_ost_changes(self):
        self.fs = self.set_and_assert_state(self.fs, "stopped")
        ost_new, ost_new_tms = ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem=self.fs)
        ObjectCache.add(ManagedTarget, ost_new.managedtarget_ptr)
        self.mgt.managedtarget_ptr = self.set_and_assert_state(freshen(self.mgt.managedtarget_ptr), "mounted")
        self.mdt.managedtarget_ptr = self.set_and_assert_state(freshen(self.mdt.managedtarget_ptr), "mounted")
        self.ost.managedtarget_ptr = self.set_and_assert_state(freshen(self.ost.managedtarget_ptr), "mounted")
        ost_new.managedtarget_ptr = self.set_and_assert_state(ost_new.managedtarget_ptr, "mounted")
        self.assertState(self.fs, "available")

        ost_new.managedtarget_ptr = self.set_and_assert_state(ost_new.managedtarget_ptr, "unmounted")
        self.assertState(self.fs, "unavailable")
        ost_new.managedtarget_ptr = self.set_and_assert_state(ost_new.managedtarget_ptr, "removed")
        self.assertState(self.fs, "available")


class TestDetectedFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestDetectedFSTransitions, self).setUp()

        self.create_simple_filesystem(self.host, start=False)

        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unformatted")
        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "unformatted")
        self.assertEqual(ManagedOst.objects.get(pk=self.ost.pk).state, "unformatted")

        self.fs = self.set_and_assert_state(self.fs, "available")

        for obj in [self.mgt, self.mdt, self.ost, self.fs]:
            obj = freshen(obj)
            obj.immutable_state = True
            obj.save()

    def test_forget(self):
        self.fs = self.set_and_assert_state(self.fs, "forgotten")
        self.mgt.managedtarget_ptr = self.set_and_assert_state(self.mgt.managedtarget_ptr, "forgotten")

        with self.assertRaises(ManagedMgs.DoesNotExist):
            freshen(self.mgt)
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            freshen(self.fs)
        with self.assertRaises(ManagedMdt.DoesNotExist):
            freshen(self.mdt)
        with self.assertRaises(ManagedOst.DoesNotExist):
            freshen(self.ost)
