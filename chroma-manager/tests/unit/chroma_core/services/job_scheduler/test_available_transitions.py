from django.contrib.contenttypes.models import ContentType
from django.db import reset_queries, connection
from django.test import TestCase
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import (ManagedMgs, ManagedFilesystem, ManagedOst,
                                ManagedMdt, RebootHostJob, ShutdownHostJob)
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_core.helper import synthetic_volume, synthetic_host

import mock


class TestAvailableTransitions(TestCase):
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
        self.js = JobScheduler()
        self.volume = synthetic_volume(with_storage=False)

        from tests.unit.chroma_core.helper import load_default_profile
        load_default_profile()

    def tearDown(self):

        super(TestAvailableTransitions, self).tearDown()

        ObjectCache.clear()

    def _get_transition_states(self, object):
        """Check that expected states are returned for given object"""

        so_ct_key = ContentType.objects.get_for_model(object).natural_key()
        so_id = object.id

        #  In-process JSC call that works over RPC in production
        receive_states = self.js.available_transitions([(so_ct_key, so_id, ), ])

        return receive_states[object.id]

    def test_managed_mgs(self):
        """Test the MGS some possible states."""

        #  No FS - mgs unformatted
        mgs = ManagedMgs.objects.create(volume=self.volume)

        expected_transitions = ['registered', 'mounted',
                                'formatted', 'unmounted', 'removed']
        received_transitions = self._get_transition_states(mgs)
        self.assertEqual(set(received_transitions), set(expected_transitions))

        # An fs causes the MGS to be non-removeable.
        ManagedFilesystem.objects.create(name='mgsfs', mgs=mgs)

        expected_transitions = ['registered', 'mounted',
                                'formatted', 'unmounted']
        received_transitions = self._get_transition_states(mgs)
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_ost(self):
        """Test the OST possible states are correct."""

        #  ost unformatted
        mgs = ManagedMgs.objects.create(volume=self.volume)
        fs = ManagedFilesystem.objects.create(name='mgsfs', mgs=mgs)
        ost = ManagedOst.objects.create(volume=self.volume,
            filesystem=fs, index=1)

        expected_transitions = ['formatted', 'registered',
                                'unmounted', 'mounted', 'removed']
        received_transitions = self._get_transition_states(ost)
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_mdt(self):
        """Test the MDT possible states are correct."""

        #  ost unformatted
        mgs = ManagedMgs.objects.create(volume=self.volume)
        fs = ManagedFilesystem.objects.create(name='mgsfs', mgs=mgs)
        mdt = ManagedMdt.objects.create(volume=self.volume,
            filesystem=fs, index=1)

        expected_transitions = ['formatted', 'registered',
                                'unmounted', 'mounted']
        received_transitions = self._get_transition_states(mdt)
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_filesystem(self):
        """Test the MDT possible states are correct."""

        #  filesystem unformatted states
        mgs = ManagedMgs.objects.create(volume=self.volume)
        fs = ManagedFilesystem.objects.create(name='mgsfs', mgs=mgs)

        expected_transitions = ['available', 'removed']
        received_transitions = self._get_transition_states(fs)
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_managed_host(self):
        """Test the MDT possible states are correct."""

        #  filesystem unformatted states
        host = synthetic_host()

        expected_transitions = ['removed', 'lnet_unloaded',
                                'lnet_up', 'lnet_down']
        received_transitions = self._get_transition_states(host)
        self.assertEqual(set(received_transitions), set(expected_transitions))

    def test_no_locks_query_count(self):
        """Check that query count to pull in available jobs hasn't changed

        If this test fails, consider changing the EXPECTED_QUERIES, or why
        it regressed.
        """

        EXPECTED_QUERIES = 0

        #  no jobs locking this object
        host = synthetic_host()

        host_ct_key = ContentType.objects.get_for_model(
            host.downcast()).natural_key()
        host_id = host.id

        #  Loads up the caches
        js = JobScheduler()

        reset_queries()
        js.available_transitions([(host_ct_key, host_id, ), ])

        query_sum = len(connection.queries)
        self.assertEqual(query_sum, EXPECTED_QUERIES,
            "something changed with queries! "
            "got %s expected %s" % (query_sum, EXPECTED_QUERIES))

    def test_locks_query_count(self):
        """Check that query count to pull in available jobs hasn't changed"""

        EXPECTED_QUERIES = 0

        #  object to be locked by jobs
        host = synthetic_host()

        host_ct_key = ContentType.objects.get_for_model(
            host.downcast()).natural_key()
        host_id = host.id

        #  create 200 host ups and down jobs in 'pending' default state
        #  key point is they are not in the 'complete' state.
        for job_num in xrange(200):
            if job_num % 2 == 0:
                RebootHostJob.objects.create(host=host)
            else:
                ShutdownHostJob.objects.create(host=host)

        #  Loads up the caches, including the _lock_cache while should find
        #  these jobs.
        js = JobScheduler()

        reset_queries()

        #  Getting jobs here may incur a higher cost.
        js.available_jobs([(host_ct_key, host_id), ])

        query_sum = len(connection.queries)
        self.assertEqual(query_sum, EXPECTED_QUERIES,
            "something changed with queries! "
            "got %s expected %s" % (query_sum, EXPECTED_QUERIES))

    def test_managed_target_dne(self):

        host = synthetic_host()
        host_ct_key = ContentType.objects.get_for_model(host.downcast()).natural_key()
        host_id = host.id

        def raise_dne(obj_content_type_natural_key, object_id):
            # Simulate the host suddenly being removed.
            raise host.DoesNotExist()

        def_to_patch = "chroma_core.services.job_scheduler.job_scheduler.JobScheduler._retrieve_stateful_object"
        with mock.patch(def_to_patch, new = staticmethod(raise_dne)):
            job_scheduler = JobScheduler()

            avail_trans = job_scheduler.available_transitions([(host_ct_key, host_id), ])[host.id]
            self.assertTrue(len(avail_trans) == 0, avail_trans)
            avail_jobs = job_scheduler.available_jobs([(host_ct_key, host_id), ])[host.id]
            self.assertTrue(len(avail_jobs) == 0)

    def test_host_deploy_failed(self):
        """Test that an undeployed host will have no transitions"""

        host = synthetic_host()
        host.state = 'deploy_failed'
        host.save()

        expected_transitions = []
        received_transitions = self._get_transition_states(host)
        self.assertEqual(set(received_transitions), set(expected_transitions))
