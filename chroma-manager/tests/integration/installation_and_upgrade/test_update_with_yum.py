from testconfig import config

from tests.integration.core.constants import UPDATE_TEST_TIMEOUT
from tests.integration.installation_and_upgrade.test_installation_and_upgrade import TestInstallationAndUpgrade


class TestYumUpdate(TestInstallationAndUpgrade):
    def test_yum_update(self):
        """ Test for lustre kernel is set to boot after yum update"""

        self.assertGreaterEqual(len(config['lustre_servers']), 4)

        # get a list of hosts
        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']
        self.assertEqual(len(hosts), len(self.TEST_SERVERS))

        # Ensure that IML notices its storage servers needs upgraded
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

        # Stop the filesystem. Currently the GUI forces you to stop the filesystem before
        # the buttons to install updates is available as we don't do a kind "rolling upgrade".
        filesystem = self.get_filesystem_by_name(self.fs_name)
        self.stop_filesystem(filesystem['id'])

        # With the list of hosts, start the upgrade as a single command
        command = self.chroma_manager.post("/api/command/", body={
            'jobs': [{'class_name': 'UpdateJob', 'args': {'host_id': host['id']}} for host in hosts],
            'message': "Test update of hosts"
        }).json

        # doing updates can include a reboot of the storage server,
        # and perhaps RHN/proxy slowness, so give it some extra time
        # Also note that IML is internally updating nodes in the same
        # HA pair in serial, so the timeout needs to be 2x.
        self.wait_for_command(self.chroma_manager, command['id'], timeout=UPDATE_TEST_TIMEOUT)
        self.wait_for_assert(lambda: self.assertNoAlerts(host['resource_uri'],
                                                         of_type='UpdatesAvailableAlert'))

        # Fully update all installed packages on the server
        for server in self.TEST_SERVERS:
            self.remote_operations.yum_update(server)
            kernel = self.remote_operations.default_boot_kernel_path(server)
            self.assertGreaterEqual(kernel.find("_lustre"), 7)

        # Start the filesystem back up
        self.start_filesystem(filesystem['id'])

    def test_no_retired_repos(self):
        "Test that no retired repos exist after an upgrade"
        retired_repos = ['xeon-phi-client']
        current_repos = self.remote_operations.get_chroma_repos()
        for repo in retired_repos:
            self.assertFalse(repo in current_repos, "Unexpectedly found repo '%s' in %s" % (repo, current_repos))
