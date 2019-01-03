import logging

from chroma_core.models import ConfigureLNetJob
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import synthetic_host


log = logging.getLogger(__name__)


class TestSortingActions(ChromaApiTestCase):
    """Test that system will sort and group all jobs and jobs via transitions

    This class mocks out job class computations, and job scheduler code:

    The emphesis is on making sure sorting and grouping works given that the
    integrated systems provide the correct information.

        JobSchedulerClient.available_jobs
        JobSchedulerClient.available_transitions

    The assumption here is that the production code, that is mocked here,
    will annotate the order and group values appropriately on the jobs
    returned.  Provided that happens, this code verifies the jobs will be sorted.
    """

    def _mock_available_jobs(self, host, expected_jobs):
        """Mock the available_jobs to return expected jobs for this host

        expected_jobs is controlled passing a list of tuples (verb, order, group)

        The JobScheduler wraps the jobs found in a dictionary.  This
        test does that wrapping in the process of this mock.
        """

        def _mock_job_dict(verb, order, group):
            return {
                "verb": verb,
                "long_description": None,
                "display_group": group,
                "display_order": order,
                "confirmation": None,
                "class_name": None,
                "args": None,
            }

        wrapped_jobs = [_mock_job_dict(verb, order, group) for verb, order, group in expected_jobs]

        @classmethod
        def _get_jobs(cls, obj_list):
            #  Return these jobs for this host only.
            return {str(host.id): wrapped_jobs}

        # ChromaApiTestCase.setup() will save off the orginal and monkey patch
        # Here we redefining the monkey patch for use in this test
        # letting the superclass set it back to what *it* saved as the original
        from chroma_core.services.job_scheduler import job_scheduler_client

        job_scheduler_client.JobSchedulerClient.available_jobs = _get_jobs

    def _mock_available_transitions(self, host, expected_jobs):
        """Mock the StatefulModelResource._add_verb method"""

        def _mock_trans_to_job_dict(verb, order, group):
            return {
                "verb": verb,
                "long_description": None,
                "display_group": group,
                "display_order": order,
                "state": None,
            }

        wrapped_jobs = [_mock_trans_to_job_dict(verb, order, group) for verb, order, group in expected_jobs]

        @classmethod
        def _get_transitions(cls, obj_list):
            #  Return these jobs for this host only.
            return {str(host.id): wrapped_jobs}

        # ChromaApiTestCase.setup() will save off the orginal and monkey patch
        # Here we redefining the monkey patch for use in this test
        # letting the superclass set it back to what *it* saved as the original
        from chroma_core.services.job_scheduler import job_scheduler_client

        job_scheduler_client.JobSchedulerClient.available_transitions = _get_transitions

    def test_sorting_actions(self):
        """Ensure direct jobs or transition jobs are sorted together."""

        host = synthetic_host()

        # These are the values the JobScheduler would return in scrambled order
        # the job.verb, job.order and job.group fields are stubbed
        self._mock_available_transitions(host, [("Job 3", 3, 2), ("Job 1", 1, 1), ("Job 6", 6, 3)])
        self._mock_available_jobs(host, [("Job 5", 5, 3), ("Job 2", 2, 1), ("Job 4", 4, 2)])

        response = self.api_client.get("/api/host/%s/" % host.id)

        self.assertHttpOK(response)
        host = self.deserialize(response)

        received_verbs_order = [t["verb"] for t in host["available_actions"]]
        expected_verbs_order = ["Job 1", "Job 2", "Job 3", "Job 4", "Job 5", "Job 6"]

        self.assertEqual(received_verbs_order, expected_verbs_order)

        received_verbs_group = [t["display_group"] for t in host["available_actions"]]
        expected_verbs_group = [1, 1, 2, 2, 3, 3]

        self.assertEqual(received_verbs_group, expected_verbs_group)

    def test_add_verb(self):
        """Test that add verb turns the jobs into the correct dictionary"""

        lnet_configuration = synthetic_host().lnet_configuration

        def _mock_get_job_class(begin_state, end_state, last_job_in_route=False):
            return ConfigureLNetJob  # a StateChangeJob

        lnet_configuration.get_job_class = _mock_get_job_class

        self.assertTrue(lnet_configuration.get_job_class(lnet_configuration.state, "ignored") == ConfigureLNetJob)
        self.assertTrue(hasattr(lnet_configuration.get_job_class(lnet_configuration.state, "ignored"), "state_verb"))

        # NB: JobScheduler._fetch_jobs takes an object, but could take a class
        jobs = JobScheduler()._add_verbs(lnet_configuration, ["ignored"])

        job_dict = jobs[0]
        self.assertTrue("verb" in job_dict)
        self.assertTrue("display_group" in job_dict)
        self.assertTrue("display_order" in job_dict)
        self.assertTrue("state" in job_dict)
        self.assertTrue("long_description" in job_dict)
