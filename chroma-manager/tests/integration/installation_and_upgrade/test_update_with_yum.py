

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.remote_operations import SimulatorRemoteOperations, RealRemoteOperations


class TestYumUpdate(ChromaIntegrationTestCase):
    TEST_SERVERS = config['lustre_servers'][0:4]

    def setUp(self):
        # connect the remote operations but otherwise...
        if config.get('simulator', False):
            self.remote_operations = SimulatorRemoteOperations(self, self.simulator)
        else:
            self.remote_operations = RealRemoteOperations(self)

        # Enable agent debugging
        self.remote_operations.enable_agent_debug(self.TEST_SERVERS)

        self.wait_until_true(self.supervisor_controlled_processes_running)
        self.initial_supervisor_controlled_process_start_times = \
            self.get_supervisor_controlled_process_start_times()

    def test_yum_update(self):
        """ Test for lustre kernel is set to boot after yum update"""

        self.assertGreaterEqual(len(config['lustre_servers']), 4)

        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']
        self.assertEqual(len(hosts), len(self.TEST_SERVERS))

        # get a list of hosts
        command = {}

        # With the list of hosts, start the upgrade
        for host in hosts:
            # wait for an upgrade available alert
            self.wait_for_assert(lambda: self.assertHasAlert(host['resource_uri'],
                                                             of_type='UpdatesAvailableAlert'))
            alerts = self.get_list("/api/alert/", {'active': True,
                                                   'alert_type': 'UpdatesAvailableAlert'})

            # Should be the only alert
            # FIXME HYD-2101 have to filter these alerts to avoid spurious ones.  Once that
            # ticket is fixed, remove the filter so that we are checking that this really is
            # the only alert systemwide as it should be.
            alerts = [a for a in alerts if a['alert_item'] == host['resource_uri']]
            self.assertEqual(len(alerts), 1)

            # Should be an 'updates needed' alert
            self.assertRegexpMatches(alerts[0]['message'], "Updates are ready.*")

            # The needs_update flag should be set on the host
            self.assertEqual(self.get_json_by_uri(host['resource_uri'])['needs_update'], True)

            # We send a command to update the storage servers with new packages
            # =================================================================
            command[host['id']] = self.chroma_manager.post("/api/command/", body={
                'jobs': [{'class_name': 'UpdateJob', 'args': {'host_id': host['id']}}],
                'message': "Test update"
            }).json

        # With the list of hosts, check the success of the upgrade, no need to actually check in parallel we will
        # just sit waiting for the longest to completed.
        for host in hosts:
            # doing updates can include a reboot of the storage server so
            # give it some extra time
            self.wait_for_command(self.chroma_manager, command[host['id']]['id'], timeout=900)
            self.wait_for_assert(lambda: self.assertNoAlerts(host['resource_uri'],
                                                             of_type='UpdatesAvailableAlert'))

        for server in self.TEST_SERVERS:
            self.remote_operations.yum_update(server)
            kernel = self.remote_operations.default_boot_kernel_path(server)
            self.assertGreaterEqual(kernel.find("_lustre"), 7)
