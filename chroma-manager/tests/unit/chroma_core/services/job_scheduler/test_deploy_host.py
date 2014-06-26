from django.test import TestCase
from chroma_core.models import DeployHostJob
from chroma_core.models import ManagedHost
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_core.helper import synthetic_host_optional_profile, freshen


class TestDeployHostJob(TestCase):
    """Test JobScheduler.create_host_ssh() """

    def test_host_available_states_undeployed(self):
        """Test that host is set to 'deploy-failed' when Job.on_error is called."""

        host = synthetic_host_optional_profile()
        host.state = 'undeployed'
        host.save()

        self.assertEquals(host.state, 'undeployed')

        # Check the available states changes depending on how installed.
        for install_method, states in {ManagedHost.INSTALL_MANUAL: [],
                                       ManagedHost.INSTALL_SSHSKY: ['configured'],
                                       ManagedHost.INSTALL_SSHPKY: ['configured'],
                                       ManagedHost.INSTALL_SSHSKY: ['configured']}.items():
            host.install_method = install_method
            self.assertEquals(host.get_available_states('undeployed'), states)

    def test_host_complete_job(self):
        """If a DeployHostJob completes in failure, the host should be in state "undeploy" """

        job_scheduler = JobScheduler()

        host = synthetic_host_optional_profile()
        host.state = 'undeployed'
        host.save()

        deploy_host_job = DeployHostJob.objects.create(managed_host=host)
        deploy_host_job.locks_json = "{}"

        job_scheduler._complete_job(deploy_host_job, errored=True, cancelled=False)

        host = freshen(host)
        self.assertEqual(host.state, 'undeployed')
