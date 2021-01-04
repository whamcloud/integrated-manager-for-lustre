from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.models import DeployHostJob
from chroma_core.models import ManagedHost
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host
from tests.unit.chroma_core.helpers.helper import freshen
from tests.unit.chroma_core.helpers.helper import load_default_profile


class TestDeployHostJob(IMLUnitTestCase):
    """Test JobScheduler.create_host_ssh() """

    def test_host_available_states_undeployed(self):
        """Test that host is set to 'deploy-failed' when Job.on_error is called."""

        load_default_profile()

        host = synthetic_host()
        host.state = "undeployed"
        host.save()

        self.assertEquals(host.state, "undeployed")

        # Check the available states changes depending on how installed.
        for install_method, states in {
            ManagedHost.INSTALL_MANUAL: [],
            ManagedHost.INSTALL_SSHSKY: ["managed"],
            ManagedHost.INSTALL_SSHPKY: ["managed"],
            ManagedHost.INSTALL_SSHSKY: ["managed"],
        }.items():
            host.install_method = install_method
            self.assertEquals(host.get_available_states("undeployed"), states)

    def test_host_complete_job(self):
        """If a DeployHostJob completes in failure, the host should be in state "undeploy" """

        job_scheduler = JobScheduler()

        load_default_profile()

        host = synthetic_host()
        host.state = "undeployed"
        host.save()

        deploy_host_job = DeployHostJob.objects.create(managed_host=host)
        deploy_host_job.locks_json = "{}"

        job_scheduler._complete_job(deploy_host_job, errored=True, cancelled=False)

        host = freshen(host)
        self.assertEqual(host.state, "undeployed")
