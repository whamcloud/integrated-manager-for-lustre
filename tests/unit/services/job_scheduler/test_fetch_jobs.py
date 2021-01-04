from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase


class TestFetchJobs(IMLUnitTestCase):
    """Test that JobScheduler._fetch_jobs works.

    This method looks for jobs that match a given obj class, and return
    a dictionary of job information suitable for returning in the API.

    _fetch_jobs() is called by available_jobs()
    """

    def setUp(self):
        super(TestFetchJobs, self).setUp()

        # Don't need to load all of JobScheduler's dependencies.
        from chroma_core.services.job_scheduler import job_scheduler

        self.old__init__ = job_scheduler.JobScheduler.__init__
        del job_scheduler.JobScheduler.__init__

        self.job_scheduler = job_scheduler.JobScheduler()

        from tests.unit.chroma_core.helpers.helper import load_default_profile

        load_default_profile()

    def tearDown(self):

        self.job_scheduler = None

        if hasattr(self, "old__init__"):
            from chroma_core.services.job_scheduler import job_scheduler

            job_scheduler.JobScheduler.__init__ = self.old__init__

    def test_normal_fetch_response(self):
        """Test that JobScheduler._fetch_jobs included required fields in response"""

        host = synthetic_host()

        # NB: _fetch_jobs takes an object, but could take a class
        jobs = self.job_scheduler._fetch_jobs(host)

        job_classes = [j["class_name"] for j in jobs]
        self.assertTrue(len(job_classes) > 0)

        job_dict = jobs[0]
        self.assertTrue("verb" in job_dict)
        self.assertTrue("display_group" in job_dict)
        self.assertTrue("display_order" in job_dict)
        self.assertTrue("confirmation" in job_dict)
        self.assertTrue("class_name" in job_dict)
        self.assertTrue("args" in job_dict)
        self.assertTrue("long_description" in job_dict)
