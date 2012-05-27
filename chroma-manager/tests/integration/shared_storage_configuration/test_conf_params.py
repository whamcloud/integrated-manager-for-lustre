
from testconfig import config
from tests.integration.core.testcases import ChromaIntegrationTestCase
from tests.utils.http_requests import AuthorizedHttpRequests


class TestConfParams(ChromaIntegrationTestCase):
    def setUp(self):
        user = config['chroma_managers'][0]['users'][0]
        self.chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
            server_http_url = config['chroma_managers'][0]['server_http_url'])
        self.reset_cluster(self.chroma_manager)

    def _create_with_params(self):
        self.hosts = self.add_hosts([config['lustre_servers'][0]['address']])

        volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(volumes), 4)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volumes = [volumes[2]]
        self.filesystem_id = self.create_filesystem(
                {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': {'lov.stripesize': '2097152'}

                },
                'osts': [{
                    'volume_id': v['id'],
                    'conf_params': {'ost.writethrough_cache_enable': '0'}
                } for v in ost_volumes],
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

        client = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client, "testfs", mount_command)

        try:
            client_hostname = config['lustre_clients'].keys()[0]
            stdin, stdout, stderr = self.remote_command(client_hostname, "cat /proc/fs/lustre/llite/*/max_cached_mb")
            self.assertEqual(stdout.read().strip(), "16")

            server_hostname = self.hosts[0]['address']
            stdin, stdout, stderr = self.remote_command(server_hostname, "cat /proc/fs/lustre/lov/testfs-MDT0000-mdtlov/stripesize")
            self.assertEqual(stdout.read().strip(), "2097152")

            stdin, stdout, stderr = self.remote_command(server_hostname, "cat /proc/fs/lustre/obdfilter/testfs-OST0000/writethrough_cache_enable")
            self.assertEqual(stdout.read().strip(), "0")
        finally:
            self.unmount_filesystem(client, 'testfs')

    def test_creation_conf_params(self):
        self._create_with_params()
        self._test_params()
        self.reset_cluster(self.chroma_manager)

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

        self.reset_cluster(self.chroma_manager)

    def test_writeconf_conf_params(self):
        self._create_with_params()
        self._test_params()

        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'UpdateNidsJob', 'args': {}}],
            'message': "Test writeconf"
        }).json
        self.wait_for_command(self.chroma_manager, command['id'])

        self.set_state("/api/filesystem/%s/" % self.filesystem_id, 'available')

        self._test_params()

        self.reset_cluster(self.chroma_manager)

    def test_update_conf_params(self):
        self.add_hosts([config['lustre_servers'][0]['address']])

        ha_volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(ha_volumes), 4)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volumes = [ha_volumes[2]]
        filesystem_id = self.create_filesystem(
                {
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

        client_hostname = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client_hostname, "testfs", mount_command)

        new_conf_params = {'llite.max_cached_mb': '16'}
        try:
            stdin, stdout, stderr = self.remote_command(client_hostname, "cat /proc/fs/lustre/llite/*/max_cached_mb")
            self.assertNotEqual(stdout.read().strip(), new_conf_params['llite.max_cached_mb'])
        finally:
            self.unmount_filesystem(client_hostname, 'testfs')

        response = self.chroma_manager.put("/api/filesystem/" + filesystem_id + "/", {'conf_params': new_conf_params})
        self.assertEqual(response.status_code, 202, response.content)
        command = response.json['command']
        filesystem = response.json['filesystem']
        self.assertDictContainsSubset(new_conf_params, filesystem['conf_params'])
        self.wait_for_command(self.chroma_manager, command['id'])

        self.mount_filesystem(client_hostname, "testfs", mount_command)

        try:
            client_hostname = config['lustre_clients'].keys()[0]
            stdin, stdout, stderr = self.remote_command(client_hostname, "cat /proc/fs/lustre/llite/*/max_cached_mb")
            self.assertEqual(stdout.read().strip(), new_conf_params['llite.max_cached_mb'])
        finally:
            self.unmount_filesystem(client_hostname, 'testfs')

        self.reset_cluster(self.chroma_manager)
