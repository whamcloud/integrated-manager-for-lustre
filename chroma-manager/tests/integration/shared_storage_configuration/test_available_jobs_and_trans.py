
import logging

from testconfig import config
from tests.integration.core.chroma_integration_testcase import (
                                                    ChromaIntegrationTestCase)

log = logging.getLogger(__name__)


class TestAvailable(ChromaIntegrationTestCase):
    """Test that the RPC to get available job and transitions works

    This test is mention to verify the RPC and endpoints are all setup and
    working over the process boundaries.  Only a basic state is tested.
    For more detailed coverage of the available_job or available_transition
    method, have a look the the job_control unit tests.
    """

    def test_available_transitions(self):
        """Test that hosts states can be looked up JobScheduler over RPC"""

        server_config_1 = config['lustre_servers'][0]

        # Add two hosts
        self.add_hosts([server_config_1['address']])

        host1 = self.get_list("/api/host/",
                              args={'fqdn': server_config_1['fqdn']})[0]

        #  Since no jobs are incomplete (could check it, but na...)
        #  We ought to get some available states, more than 1 at least.
        for trans in host1['available_transitions']:
            self.assertIn(trans['state'], ['lnet_up', 'lnet_down', 'lnet_unloaded', 'removed'])

    def test_available_jobs(self):
        """Test that hosts job can be looked on the JobScheduler over RPC"""

        server_config_1 = config['lustre_servers'][0]

        # Add two hosts
        self.add_hosts([server_config_1['address']])

        host1 = self.get_list("/api/host/",
            args={'fqdn': server_config_1['fqdn']})[0]

        #  Since no jobs are incomplete (could check it, but na...)
        #  We ought to get some available states, more than 1 at least.
        returned_jobs = [job['class_name'] for job in host1['available_jobs']]
        expected_jobs = ['ForceRemoveHostJob', 'RebootHostJob', 'ShutdownHostJob']
        self.assertEqual(set(returned_jobs), set(expected_jobs))
