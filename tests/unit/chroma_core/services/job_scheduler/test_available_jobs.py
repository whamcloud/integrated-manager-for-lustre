from django.contrib.contenttypes.models import ContentType

from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import RebootHostJob, ShutdownHostJob
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host
from tests.unit.chroma_core.helpers.helper import create_simple_fs


class TestAvailableJobs(EMFUnitTestCase):
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

        from chroma_core.services.job_scheduler.job_scheduler import JobScheduler

        from tests.unit.chroma_core.helpers.helper import load_default_profile

        load_default_profile()

        self.JobScheduler = JobScheduler
        self.js = JobScheduler()

        # Create object before ObjectCache init, so they are in the cache.
        self.host = synthetic_host()

        (mgt, fs, mdt, ost) = create_simple_fs()

        self.mgs = mgt
        self.fs = fs
        self.mdt = mdt
        self.ost = ost

        # If you create object after init of this case, they will not be in it.
        ObjectCache.getInstance()

    def tearDown(self):

        super(TestAvailableJobs, self).tearDown()

        ObjectCache.clear()

    def _fake_add_lock(self, jobscheduler, object, new_state):

        d = (ContentType.objects.get_for_model(object).natural_key(), object.id, new_state)
        jobscheduler.set_state([d], "fake object lock", run=False)

    def _get_jobs(self, object):
        """Check that expected states are returned for given object"""

        ct_id = ContentType.objects.get_for_model(object).id
        so_id = object.id

        #  In-process JSC call that works over RPC in production
        receive_jobs = self.js.available_jobs([(ct_id, so_id)])

        return receive_jobs["{}:{}".format(ct_id, so_id)]

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

        EXPECTED_QUERIES = 4

        host_ct_key = ContentType.objects.get_for_model(self.host.downcast()).natural_key()
        host_id = self.host.id

        #  Loads up the caches
        js = self.JobScheduler()

        with self.assertNumQueries(EXPECTED_QUERIES):
            js.available_jobs([(host_ct_key, host_id)])

    def test_locks_query_count(self):
        """Check that query count to pull in available jobs hasn't changed"""

        EXPECTED_QUERIES = 6

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
        js = self.JobScheduler()

        #  Getting jobs here may incur a higher cost.
        with self.assertNumQueries(EXPECTED_QUERIES):
            js.available_jobs([(host_ct_key, host_id)])

    def test_object_is_locked(self):
        js = self.JobScheduler()
        self._fake_add_lock(js, self.host.lnet_configuration, "lnet_up")

        lnet_configuration_ct_key = ContentType.objects.get_for_model(
            self.host.lnet_configuration.downcast()
        ).natural_key()
        lnet_configuration_id = self.host.lnet_configuration.id

        locks = js.get_locks()

        xss = locks.values()
        self.assertEqual(len(xss), 1)

        xs = xss.pop()

        self.assertEqual(len(xs), 2)
        self.assertEqual(len([x for x in xs if x.get("lock_type") == "write"]), 2)

    def test_managed_host_undeployed(self):
        """Test that an undeployed host can only be force removed"""

        self.host.state = "undeployed"
        self.host.save()

        ObjectCache.update(self.host)

        expected_job_classes = ["ForceRemoveHostJob"]
        received_job_classes = [job["class_name"] for job in self._get_jobs(self.host)]
        self.assertEqual(set(received_job_classes), set(expected_job_classes))
