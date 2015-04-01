from testconfig import config

from tests.integration.core.constants import UPDATE_TEST_TIMEOUT
from tests.integration.installation_and_upgrade.test_create_filesystem \
    import TestCreateFilesystem, my_setUp


class TestYumUpdate(TestCreateFilesystem):

    def setUp(self):
        my_setUp(self)

    def test_create(self):
        """ Test that a filesystem can be created"""

        self.assertGreaterEqual(len(config['lustre_servers']), 4)

        self.hosts = self.add_hosts([
            config['lustre_servers'][0]['address'],
            config['lustre_servers'][1]['address'],
            config['lustre_servers'][2]['address'],
            config['lustre_servers'][3]['address']
        ])

        volumes = self.wait_for_shared_volumes(4, 4)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost1_volume = volumes[2]
        ost2_volume = volumes[3]
        self.set_volume_mounts(mgt_volume, self.hosts[0]['id'], self.hosts[1]['id'])
        self.set_volume_mounts(mdt_volume, self.hosts[1]['id'], self.hosts[0]['id'])
        self.set_volume_mounts(ost1_volume, self.hosts[2]['id'], self.hosts[3]['id'])
        self.set_volume_mounts(ost2_volume, self.hosts[3]['id'], self.hosts[2]['id'])

        # By providing mdts and mdt we can cope with 2.2 and 2.3. 2.2 required a single mdt, 2.3 required mdts.
        self.filesystem_id = self.create_filesystem({
            'name': self.fs_name,
            'mgt': {'volume_id': mgt_volume['id']},
            'mdt': {
                'volume_id': mdt_volume['id'],
                'conf_params': {}
            },
            'mdts': [{
                'volume_id': mdt_volume['id'],
                'conf_params': {}

            }],
            'osts': [{
                'volume_id': ost1_volume['id'],
                'conf_params': {}
            }, {
                'volume_id': ost2_volume['id'],
                'conf_params': {}
            }],
            'conf_params': {}
        })

        self._exercise_simple(self.filesystem_id)

        self.assertTrue(self.get_filesystem_by_name(self.fs_name)['name'] == self.fs_name)

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

        # With the list of hosts, start the upgrade
        command = {}
        for host in hosts:
            # We send a command to update the storage servers with new packages
            # =================================================================
            command[host['id']] = self.chroma_manager.post("/api/command/", body={
                'jobs': [{'class_name': 'UpdateJob', 'args': {'host_id': host['id']}}],
                'message': "Test update"
            }).json

        # With the list of hosts, check the success of the upgrade, no need to actually check in parallel we will
        # just sit waiting for the longest to completed.
        for host in hosts:
            # doing updates can include a reboot of the storage server,
            # and perhaps RHN/proxy slowness, so give it some extra time
            # Also note that IML is internally updating nodes in the same
            # HA pair in serial, so the timeout needs to be 2x.
            self.wait_for_command(self.chroma_manager, command[host['id']]['id'], timeout=UPDATE_TEST_TIMEOUT)
            self.wait_for_assert(lambda: self.assertNoAlerts(host['resource_uri'],
                                                             of_type='UpdatesAvailableAlert'))

        # Fully update all installed packages on the server
        for server in self.TEST_SERVERS:
            self.remote_operations.yum_update(server)
            kernel = self.remote_operations.default_boot_kernel_path(server)
            self.assertGreaterEqual(kernel.find("_lustre"), 7)

        # Start the filesystem back up
        self.start_filesystem(filesystem['id'])
