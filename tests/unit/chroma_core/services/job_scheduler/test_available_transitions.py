from django.contrib.contenttypes.models import ContentType
from django.db import reset_queries, connection

from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import ManagedMgs, ManagedFilesystem, ManagedOst, ManagedMdt, RebootHostJob, ShutdownHostJob
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_core.helpers import synthetic_volume, synthetic_host
from tests.unit.chroma_core.helpers import load_default_profile


class TestAvailableTransitions(IMLUnitTestCase):
    """Check that available transitions are reported correctly

    Testing the JobScheduler.available_tranistions method

    Inputs:  ManagedMgs, ManagedOst, ManagedMdt, ManagedFilesystem, ManagedHost

    Test cases:
      Check transition states correct when no incomplete jobs
      Check transition states are empty when there are incomplete jobs

    Note: Future implementation might try to return some states when there
    are incomplete jobs.  If that is implemented, this test will need
    to be updated.

    Note: Might be nice to add to these tests all the different starting
    states, to get complete coverage.

    """

    def setUp(self):
        super(TestAvailableTransitions, self).setUp()

        self.js = JobScheduler()

        load_default_profile()

        self.host = synthetic_host()
        self.assertEqual(self.host.state, "managed")

    def tearDown(self):

        super(TestAvailableTransitions, self).tearDown()

        ObjectCache.clear()

    def _get_transition_states(self, object):
        """Check that expected states are returned for given object"""

        ct_id = ContentType.objects.get_for_model(object).id
        so_id = object.id

        #  In-process JSC call that works over RPC in production
        receive_states = self.js.available_transitions([(ct_id, so_id)])

        return receive_states["{}:{}".format(ct_id, so_id)]

    def test_managed_mgs(self):
        """Test the MGS some possible states."""

        #  No FS - mgs unformatted
        mgs = ManagedMgs.objects.create()

        expected_transitions = []
        received_transitions = [t["state"] for t in self._get_transition_states(mgs)]
        self.assertEqual(set(received_transitions), set(expected_transitions))

        # An fs causes the MGS to be non-removeable.
        ManagedFilesystem.objects.create(name="mgsfs", mgs=mgs)

        expected_transitions = []
        received_transitions = [t["state"] for t in self._get_transition_states(mgs)]
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_ost(self):
        """Test the OST possible states are correct."""

        #  ost unformatted
        mgs = ManagedMgs.objects.create()
        fs = ManagedFilesystem.objects.create(name="mgsfs", mgs=mgs)
        ost = ManagedOst.objects.create(filesystem=fs, index=1)

        expected_transitions = []
        received_transitions = [t["state"] for t in self._get_transition_states(ost)]
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_root_mdt(self):
        """Test the MDT possible states are correct."""

        #  ost unformatted
        mgs = ManagedMgs.objects.create()
        fs = ManagedFilesystem.objects.create(name="mgsfs", mgs=mgs)
        mdt = ManagedMdt.objects.create(filesystem=fs, index=0)

        expected_transitions = []
        received_transitions = [t["state"] for t in self._get_transition_states(mdt)]
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_mdt(self):
        """Test the MDT possible states are correct."""

        #  ost unformatted
        mgs = ManagedMgs.objects.create()
        fs = ManagedFilesystem.objects.create(name="mgsfs", mgs=mgs)
        mdt = ManagedMdt.objects.create(filesystem=fs, index=1)

        expected_transitions = []
        received_transitions = [t["state"] for t in self._get_transition_states(mdt)]
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_filesystem(self):
        """Test the MDT possible states are correct."""

        #  filesystem unformatted states
        mgs = ManagedMgs.objects.create()
        fs = ManagedFilesystem.objects.create(name="mgsfs", mgs=mgs)

        expected_transitions = ["available", "forgotten"]
        received_transitions = [t["state"] for t in self._get_transition_states(fs)]
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_host(self):
        """Test the MDT possible states are correct."""

        #  filesystem unformatted states
        expected_transitions = ["removed"]
        received_transitions = [t["state"] for t in self._get_transition_states(self.host)]
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_lnet_configuration(self):
        """Test the lnet_configuration possible states are correct."""

        #  lnet configuration states
        test_transitions = {
            "unconfigured": [
                "lnet_down",
                "lnet_up",
            ],  # lnet_unloaded is not advertised from unconfigured and so doesn't appear
            "lnet_unloaded": ["lnet_down", "lnet_up"],
            "lnet_down": ["lnet_unloaded", "lnet_up"],
            "lnet_up": ["lnet_unloaded", "lnet_down"],
        }

        for test_state, expected_transitions in test_transitions.items():
            self.host.lnet_configuration.state = test_state
            self.host.lnet_configuration.save()

            received_transitions = [t["state"] for t in self._get_transition_states(self.host.lnet_configuration)]
            self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_no_locks_query_count(self):
        """Check that query count to pull in available jobs hasn't changed

        If this test fails, consider changing the EXPECTED_QUERIES, or why
        it regressed.
        """

        EXPECTED_QUERIES = 0

        #  no jobs locking this object
        host_ct_key = ContentType.objects.get_for_model(self.host.downcast()).natural_key()
        host_id = self.host.id

        #  Loads up the caches
        js = JobScheduler()

        reset_queries()
        js.available_transitions([(host_ct_key, host_id)])

        query_sum = len(connection.queries)
        self.assertEqual(
            query_sum,
            EXPECTED_QUERIES,
            "something changed with queries! " "got %s expected %s" % (query_sum, EXPECTED_QUERIES),
        )

    def test_locks_query_count(self):
        """Check that query count to pull in available jobs hasn't changed"""

        EXPECTED_QUERIES = 0

        #  object to be locked by jobs
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
        self.assertEqual(
            query_sum,
            EXPECTED_QUERIES,
            "something changed with queries! " "got %s expected %s" % (query_sum, EXPECTED_QUERIES),
        )

    def test_managed_target_dne(self):
        ct_id = ContentType.objects.get_for_model(self.host.downcast()).id
        host_id = self.host.id

        self.host.mark_deleted()

        job_scheduler = JobScheduler()

        composite_id = "{}:{}".format(ct_id, host_id)

        avail_trans = job_scheduler.available_transitions([(ct_id, host_id)])[composite_id]
        self.assertTrue(len(avail_trans) == 0, avail_trans)
        avail_jobs = job_scheduler.available_jobs([(ct_id, host_id)])[composite_id]
        self.assertTrue(self.host.state, "managed")
        self.assertTrue(len(avail_jobs) == 3)  # Three states from configured -> Force Remove. Reboot, Shutdown
