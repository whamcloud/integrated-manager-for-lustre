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


class TestFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestFSTransitions, self).setUp()

        self.create_simple_filesystem(start=False)
        self.assertEqual(self.mgt.state, "unmounted")
        self.assertEqual(self.mdt.state, "unmounted")
        self.assertEqual(self.ost.state, "unmounted")

        self.fs = self.set_and_assert_state(self.fs, "available")

        self.assertState(self.mgt, "mounted")
        self.assertState(self.mdt, "mounted")
        self.assertState(self.ost, "mounted")
        self.assertState(self.fs, "available")

    def test_target_stop(self):
        from chroma_core.models import ManagedMdt, ManagedFilesystem

        self.mdt.managedtarget_ptr = self.set_and_assert_state(self.mdt.managedtarget_ptr, "unmounted")
        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "unmounted")
        self.assertEqual(ManagedFilesystem.objects.get(pk=self.fs.pk).state, "available")

    def test_target_start(self):
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem

        self.fs = self.set_and_assert_state(self.fs, "stopped")
        self.mdt.managedtarget_ptr = self.set_and_assert_state(freshen(self.mdt.managedtarget_ptr), "mounted")

        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "mounted")
        self.assertEqual(ManagedOst.objects.get(pk=self.ost.pk).state, "unmounted")
        self.assertEqual(ManagedFilesystem.objects.get(pk=self.fs.pk).state, "stopped")

        self.ost.managedtarget_ptr = self.set_and_assert_state(freshen(self.ost.managedtarget_ptr), "mounted")
        self.assertState(self.fs, "stopped")

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


class TestDetectedFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestDetectedFSTransitions, self).setUp()

        self.create_simple_filesystem(start=False)

        self.assertEqual(ManagedMgs.objects.get(pk=self.mgt.pk).state, "unmounted")
        self.assertEqual(ManagedMdt.objects.get(pk=self.mdt.pk).state, "unmounted")
        self.assertEqual(ManagedOst.objects.get(pk=self.ost.pk).state, "unmounted")

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
