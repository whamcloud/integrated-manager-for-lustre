from testconfig import config

from tests.integration.core.chroma_integration_testcase import AuthorizedTestCase


class TestConfParams(AuthorizedTestCase):
    def _create_with_params(self):
        self.hosts = self.add_hosts([
            config['lustre_servers'][0]['address'],
            config['lustre_servers'][1]['address'],
        ])

        volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(volumes), 4)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volume = volumes[2]
        self.set_volume_mounts(mgt_volume, self.hosts[0]['id'], self.hosts[1]['id'])
        self.set_volume_mounts(mdt_volume, self.hosts[0]['id'], self.hosts[1]['id'])
        self.set_volume_mounts(ost_volume, self.hosts[0]['id'], self.hosts[1]['id'])

        self.filesystem_id = self.create_filesystem(
                {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': {'lov.stripesize': '2097152'}

                },
                'osts': [{
                    'volume_id': ost_volume['id'],
                    'conf_params': {'ost.writethrough_cache_enable': '0'}
                }],
                'conf_params': {'llite.max_cached_mb': '16'}
            }
        )

    def _test_params(self):
        # Mount the filesystem
        response = self.chroma_manager.get(
            '/api/filesystem/',
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json['objects']), 1)
        filesystem = response.json['objects'][0]

        mount_command = filesystem['mount_command']
        self.assertTrue(mount_command)

        client = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client, "testfs", mount_command)

        try:
            client_hostname = config['lustre_clients'].keys()[0]
            result = self.remote_command(client_hostname, "cat /proc/fs/lustre/llite/*/max_cached_mb")
            self.assertEqual(result.stdout.read().strip(), "16")

            server_hostname = self.hosts[0]['address']
            result = self.remote_command(server_hostname, "cat /proc/fs/lustre/lov/testfs-MDT0000-mdtlov/stripesize")
            self.assertEqual(result.stdout.read().strip(), "2097152")

            result = self.remote_command(server_hostname, "cat /proc/fs/lustre/obdfilter/testfs-OST0000/writethrough_cache_enable")
            self.assertEqual(result.stdout.read().strip(), "0")
        finally:
            self.unmount_filesystem(client, 'testfs')

    def test_creation_conf_params(self):
        self._create_with_params()
        self._test_params()
        self.graceful_teardown(self.chroma_manager)

    def test_dumpload_conf_params(self):
        self._create_with_params()
        self.filesystem_id = 1
        self.hosts = self.chroma_manager.get('/api/host/').json['objects']
        #self._test_params()

        # Check that conf params are properly preserved across a dump/load of the configuration

        # Save configuration
        response = self.chroma_manager.get("/api/configuration/")
        self.assertEqual(response.status_code, 200)
        configuration = response.json

        # Clear running system
        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': self.hosts[0]['id']}}],
            'message': "Test force remove hosts"
        }).json
        self.wait_for_command(self.chroma_manager, command['id'])

        # Resurrect configuration
        self.hosts = self.add_hosts([config['lustre_servers'][0]['address']])
        response = self.chroma_manager.post("/api/configuration/", body = configuration)
        self.assertEqual(response.status_code, 201)

        self._test_params()

        self.graceful_teardown(self.chroma_manager)

    def test_writeconf_conf_params(self):
        self._create_with_params()
        self._test_params()

        # Check that conf params are preserved across a writeconf
        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'UpdateNidsJob', 'args': {}}],
            'message': "Test writeconf"
        }).json
        self.wait_for_command(self.chroma_manager, command['id'])

        fs_uri = "/api/filesystem/%s/" % self.filesystem_id
        response = self.chroma_manager.get(fs_uri)
        self.assertEqual(response.status_code, 200)
        fs = response.json

        # FIXME: HYD-1133: have to manually ensure the MGT comes up first
        # after a writeconf
        self.set_state(fs['mgt']['resource_uri'], 'mounted')
        self.set_state(fs['mdts'][0]['resource_uri'], 'mounted')
        self.set_state(fs['resource_uri'], 'available')

        self._test_params()

        self.graceful_teardown(self.chroma_manager)

    def test_update_conf_params(self):
        self.add_hosts([config['lustre_servers'][0]['address']])

        ha_volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(ha_volumes), 4)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volumes = [ha_volumes[2]]
        filesystem_id = self.create_filesystem({
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': {}
                },
                'osts': [{
                    'volume_id': v['id'],
                    'conf_params': {}
                } for v in ost_volumes],
                'conf_params': {}
            }
        )

        # Mount the filesystem
        response = self.chroma_manager.get(
            '/api/filesystem/%s/' % filesystem_id,
        )
        self.assertEqual(response.successful, True, response.text)
        mount_command = response.json['mount_command']
        self.assertTrue(mount_command)

        client_hostname = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client_hostname, "testfs", mount_command)

        new_conf_params = {'llite.max_cached_mb': '16'}
        try:
            result = self.remote_command(client_hostname, "cat /proc/fs/lustre/llite/*/max_cached_mb")
            self.assertNotEqual(result.stdout.read().strip(), new_conf_params['llite.max_cached_mb'])
        finally:
            self.unmount_filesystem(client_hostname, 'testfs')

        filesystem = self.chroma_manager.get("/api/filesystem/" + filesystem_id + "/").json
        for k, v in new_conf_params.items():
            filesystem['conf_params'][k] = v
        response = self.chroma_manager.put(filesystem['resource_uri'], filesystem)
        self.assertEqual(response.status_code, 202, response.content)
        command = response.json['command']
        filesystem = response.json['filesystem']
        self.assertDictContainsSubset(new_conf_params, filesystem['conf_params'])
        self.wait_for_command(self.chroma_manager, command['id'])

        self.mount_filesystem(client_hostname, "testfs", mount_command)

        try:
            client_hostname = config['lustre_clients'].keys()[0]
            result = self.remote_command(client_hostname, "cat /proc/fs/lustre/llite/*/max_cached_mb")
            self.assertEqual(result.stdout.read().strip(), new_conf_params['llite.max_cached_mb'])
        finally:
            self.unmount_filesystem(client_hostname, 'testfs')

        self.graceful_teardown(self.chroma_manager)
