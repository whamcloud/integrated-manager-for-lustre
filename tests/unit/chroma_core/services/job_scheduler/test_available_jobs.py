from django.contrib.contenttypes.models import ContentType
from django.db import connection, reset_queries

from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import ManagedMgs, ManagedFilesystem, ManagedOst, ManagedMdt, RebootHostJob, ShutdownHostJob
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_core.helpers import synthetic_volume, synthetic_host


class TestAvailableJobs(IMLUnitTestCase):
    """Check that available jobs are reported correctly

    Testing the JobScheduler.available_jobs method

    Inputs:  ManagedMgs, ManagedOst, ManagedMdt, ManagedFilesystem
    and ManagedHost

    Test cases:
      Check returned jobs are correct when no incomplete jobs
      Check returned jobs are empty when there are incomplete jobs
    """

    def setUp(self):

        super(TestAvailableJobs, self).setUp()

        from tests.unit.chroma_core.helpers import load_default_profile

        load_default_profile()

        self.js = JobScheduler()
        volume = synthetic_volume(with_storage=False)

        # Create object before ObjectCache init, so they are in the cache.
        self.host = synthetic_host()
        self.mgs = ManagedMgs.objects.create(volume=volume)
        self.fs = ManagedFilesystem.objects.create(name="mgsfs", mgs=self.mgs)
        self.mdt = ManagedMdt.objects.create(volume=volume, filesystem=self.fs, index=1)
        self.ost = ManagedOst.objects.create(volume=volume, filesystem=self.fs, index=1)

        # If you create object after init of this case, they will not be in it.
        ObjectCache.getInstance()

        connection.use_debug_cursor = True

    def tearDown(self):

        super(TestAvailableJobs, self).tearDown()

        ObjectCache.clear()

        connection.use_debug_cursor = False

    def _fake_add_lock(self, jobscheduler, object, new_state):

        d = (ContentType.objects.get_for_model(object).natural_key(), object.id, new_state)
        jobscheduler.set_state([d], "fake object lock", run=False)

    def _get_jobs(self, object):
        """Check that expected states are returned for given object"""

        so_ct_key = ContentType.objects.get_for_model(object).natural_key()
        so_id = object.id

        #  In-process JSC call that works over RPC in production
        receive_jobs = self.js.available_jobs([(so_ct_key, so_id)])

        return receive_jobs[object.id]

    def test_managed_mgs(self):
        """Test the MGS available jobs."""

        expected_job_classes = []
        received_job_classes = [job["class_name"] for job in self._get_jobs(self.mgs)]
        self.assertEqual(set(received_job_classes), set(expected_job_classes))

    def test_managed_ost(self):
        """Test the OST available jos"""

        expected_job_classes = []
        received_job_classes = [job["class_name"] for job in self._get_jobs(self.ost)]
        self.assertEqual(set(received_job_classes), set(expected_job_classes))

    def test_managed_host(self):
        """Test the MDT possible states are correct."""

        expected_job_classes = ["ShutdownHostJob", "RebootHostJob", "ForceRemoveHostJob"]
        received_job_classes = [job["class_name"] for job in self._get_jobs(self.host)]
        self.assertEqual(set(received_job_classes), set(expected_job_classes))

    def test_managed_filesystem(self):
        """Test the MDT possible states are correct."""

        expected_job_classes = []
        received_job_classes = [job["class_name"] for job in self._get_jobs(self.fs)]

        self.assertEqual(set(received_job_classes), set(expected_job_classes))

    def test_managed_mdt(self):
        """Test the MDT possible states are correct."""

        expected_job_classes = []
        received_job_classes = [job["class_name"] for job in self._get_jobs(self.mdt)]

        self.assertEqual(set(received_job_classes), set(expected_job_classes))

    def test_no_locks_query_count(self):
        """Check that query count to pull in available jobs hasn't changed

        If this test fails, consider changing the EXPECTED_QUERIES, or why
        it regressed.
        """

        # 20131217 - mjmac: bumped to 7 for new Client management jobs
        # 20141007 - chris: change to 5 because some objects are now in the ObjectCache
        EXPECTED_QUERIES = 5  # but 3 are for setup

        host_ct_key = ContentType.objects.get_for_model(self.host.downcast()).natural_key()
        host_id = self.host.id

        #  Loads up the caches
        js = JobScheduler()

        reset_queries()
        js.available_jobs([(host_ct_key, host_id)])

        query_sum = len(connection.queries)
        self.assertEqual(
            query_sum,
            EXPECTED_QUERIES,
            "something changed with queries! " "got %s expected %s" % (query_sum, EXPECTED_QUERIES),
        )

    def test_locks_query_count(self):
        """Check that query count to pull in available jobs hasn't changed"""

        EXPECTED_QUERIES = 6  # but 3 are for setup

        host_ct_key = ContentType.objects.get_for_model(self.host.downcast()).natural_key()
        host_id = self.host.id

        #  create 200 host ups and down jobs in 'pending' default state
        #  key point is they are not in the 'complete' state.
        for job_num in xrange(200):
            if job_num % 2 == 0:
                RebootHostJob.objects.create(host=self.host)
            else:
                ShutdownHostJob.objects.create(host=self.host)

        #  Loads up the caches, including the _lock_cache while should find
        #  these jobs.
        js = JobScheduler()

        reset_queries()

        #  Getting jobs here may incur a higher cost.
        js.available_jobs([(host_ct_key, host_id)])

        query_sum = len(connection.queries)
        self.assertGreaterEqual(
            query_sum,
            EXPECTED_QUERIES,
            "something changed with queries! " "got %s expected %s" % (query_sum, EXPECTED_QUERIES),
        )

    def test_object_is_locked(self):
        js = JobScheduler()
        self._fake_add_lock(js, self.host.lnet_configuration, "lnet_up")

        lnet_configuration_ct_key = ContentType.objects.get_for_model(
            self.host.lnet_configuration.downcast()
        ).natural_key()
        lnet_configuration_id = self.host.lnet_configuration.id

        locks = js.get_locks(lnet_configuration_ct_key, lnet_configuration_id)
        self.assertFalse(locks["read"])
        self.assertEqual(2, len(locks["write"]))

    def test_managed_host_undeployed(self):
        """Test that an undeployed host can only be force removed"""

        self.host.state = "undeployed"
        self.host.save()

        ObjectCache.update(self.host)

        expected_job_classes = ["ForceRemoveHostJob"]
        received_job_classes = [job["class_name"] for job in self._get_jobs(self.host)]
        self.assertEqual(set(received_job_classes), set(expected_job_classes))
