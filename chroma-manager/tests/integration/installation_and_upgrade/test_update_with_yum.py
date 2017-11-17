from subprocess import check_output
from testconfig import config

from django.utils.unittest import skip

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
        self.assertEqual(len(hosts), len(self.config_servers))

        # Even though we have to stop a filesytem to do an upgrade (i.e. no
        # rolling upgrades, we stopped it before doing the upgrade to avoid
        # situations where the O/S upgrade results in an IML that can no
        # longer function with the upgraded O/S.

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
        for server in self.config_servers:
            self.remote_operations.yum_update(server)
            kernel = self.remote_operations.default_boot_kernel_path(server)
            self.assertGreaterEqual(kernel.find("_lustre"), 7)

    @skip("Repos can't really be retired until at least an n+1 release")
    def test_no_retired_repos(self):
        "Test that no retired repos exist after an upgrade"
        # TODO: this really needs to be more dynamic than using
        #       repos that would have been retired many re-
        #       leases ago
        retired_repos = ['robinhood']
        current_repos = self.remote_operations.get_chroma_repos()
        for repo in retired_repos:
            self.assertFalse(repo in current_repos, "Unexpectedly found repo '%s' in %s" % (repo, current_repos))

    def test_obsolete_chroma_diagnostics(self):
        """Test that chroma-diagnostics has been obsoleted"""
        servers = config['lustre_servers']
        addresses = [server['address'] for server in servers]
        
        for address in addresses:
            result = self.remote_command(address, 'chroma-diagnostics')
            self.assertEqual(result.stdout.split('\n')[0], "chroma-diagnostics no longer exists. Please use 'iml-diagnostics' instead.")

    # something we can run to clear the storage targets since this
    # test class doesn't use setUp()
    def test_clean_linux_devices(self):
        self.cleanup_linux_devices(self.TEST_SERVERS)

    def test_stop_before_update(self):
        # Stop the filesystem. Currently the GUI forces you to stop the filesystem before
        # the buttons to install updates is available as we don't do a kind "rolling upgrade".
        filesystem = self.get_filesystem_by_name(self.fs_name)
        if filesystem['state'] != "stopped":
            self.stop_filesystem(filesystem['id'])
