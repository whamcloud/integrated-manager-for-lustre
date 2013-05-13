from django.utils.unittest.case import skipIf
from testconfig import config

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


@skipIf(not config.get('simulator', False), "Automated test of upgrades is HYD-1739")
class TestConfParams(ChromaIntegrationTestCase):
    TEST_SERVERS = [config['lustre_servers'][0]]

    def test_upgrade_alerting(self):
        """
        Test that when a server reports some upgrades available, the manager raises
        an appropriate alert, and that when an upgrade job completes successfully
        this alert is cleared.
        """

        # Initially a chroma-manager is installed and a server is set up
        # ===============================================================

        host = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        packages = self.get_list("/api/package/", {'host': host['id'], 'limit': 0})
        original_packages = {}
        for p in packages:
            if host['resource_uri'] in p['installed_hosts']:
                original_packages[p['name']] = (p['epoch'], p['version'], p['release'], p['arch'])

        self.assertNotEqual(len(original_packages), 0)

        # No alerts should be high at this point
        self.assertNoAlerts(host['resource_uri'])

        # Subsequently chroma-manager is upgraded
        # =======================================
        self.remote_operations.install_upgrades()

        # The causes the agent to see higher versions of available packages, so an
        # alert is raised to indicate the need to upgrade
        self.wait_for_assert(lambda: self.assertHasAlert(host['resource_uri']))
        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})

        # Should be the only alert
        # FIXME HYD-2101 have to filter these alerts to avoid spurious ones.  Once that
        # ticket is fixed, remove the filter so that we are checking that this really is
        # the only alert systemwide as it should be.
        alerts = [a for a in alerts if a['alert_item'] == host['resource_uri']]
        self.assertEqual(len(alerts), 1)

        # Should be an 'updates needed' alert
        self.assertRegexpMatches(alerts[0]['message'], "Updates are ready.*")

        # The needs_update flag should be set on the host
        self.assertEqual(self.get_by_uri(host['resource_uri'])['needs_update'], True)

        # Get the hosts package list and check that the available updates are represented
        packages = self.get_list("/api/package/", {'host': host['id'], 'limit': 0})
        upgrade_packages = {}

        for p in packages:
            if not host['resource_uri'] in p['installed_hosts']:
                upgrade_version = (p['epoch'], p['version'], p['release'], p['arch'])
                upgrade_packages[p['name']] = upgrade_version

                # Sanity: this upgrade should be a different version to what was initially installed
                self.assertNotEqual(original_packages[p['name']], upgrade_version)

        # There should be at least one upgrade available
        self.assertGreater(len(upgrade_packages), 0)

        # We send a command to update the storage servers with new packages
        # =================================================================
        command = self.chroma_manager.post("/api/command/", body={
            'jobs': [{'class_name': 'UpdateJob', 'args': {'host_id': host['id']}}],
            'message': "Test update"
        }).json
        self.wait_for_command(self.chroma_manager, command['id'])
        self.wait_for_assert(lambda: self.assertNoAlerts(host['resource_uri']))

        # Check that a new package really did get installed
        for package_name, package_version in upgrade_packages.items():
            new_version = self.remote_operations.get_package_version(host['fqdn'], package_name)
            self.assertEqual(package_version, new_version)
