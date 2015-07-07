

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.remote_operations import SimulatorRemoteOperations, RealRemoteOperations


class TestCreateFilesystem(ChromaIntegrationTestCase):
    TEST_SERVERS = config['lustre_servers'][0:4]
    fs_name = "testfs"

    def add_hosts(self, addresses, auth_type='existing_keys_choice'):
        # Override add hosts functionality for older APIs

        # if the host_profile api endpoint exists or using simulator, can use current logic
        response = self.chroma_manager.get('/api/host_profile/')
        if response.successful or hasattr(self, 'simulator'):
            super(TestCreateFilesystem, self).add_hosts(addresses, auth_type)
        else:
            # otherwise we need to use the old way of adding hosts
            host_create_command_ids = []
            for host_address in addresses:
                profile = self.get_host_profile(host_address)
                response = self.chroma_manager.post(
                    '/api/test_host/',
                    body = {
                        'address': host_address,
                        'server_profile': profile['resource_uri']
                    }
                )
                self.assertTrue(response.successful, response.text)
                response = self.chroma_manager.post(
                    '/api/host/',
                    body = {
                        'address': host_address,
                        'server_profile': profile['resource_uri']
                    }
                )
                self.assertTrue(response.successful, response.text)
                host_create_command_ids.append(response.json['command']['id'])
            self.wait_for_commands(self.chroma_manager, host_create_command_ids, timeout=1800)
            new_hosts = self.get_hosts(addresses)
            self.assertEqual(len(new_hosts), len(addresses), "Hosts found: '%s'" % new_hosts)
            self.remote_operations.sync_disks(new_hosts)
            return new_hosts

    def _exercise_simple(self, fs_id):
        filesystem = self.get_filesystem(fs_id)
        client = config['lustre_clients'][0]['address']
        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_operations.exercise_filesystem(client, filesystem)
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

    def test_create(self):
        """ Test that a filesystem can be created"""

        self.assertGreaterEqual(len(config['lustre_servers']), 4)

        hosts = self.add_hosts([
            config['lustre_servers'][0]['address'],
            config['lustre_servers'][1]['address'],
        ])

        volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(volumes), 3)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost_volume = volumes[2]
        self.set_volume_mounts(mgt_volume, hosts[0]['id'], hosts[1]['id'])
        self.set_volume_mounts(mdt_volume, hosts[1]['id'], hosts[0]['id'])
        self.set_volume_mounts(ost_volume, hosts[0]['id'], hosts[1]['id'])

        filesystem_id = self.create_filesystem({
            'name': self.fs_name,
            'mgt': {'volume_id': mgt_volume['id']},
            'mdts': [{
                'volume_id': mdt_volume['id'],
                'conf_params': {}

            }],
            'osts': [{
                'volume_id': ost_volume['id'],
                'conf_params': {}
            }],
            'conf_params': {}
        })

        self._exercise_simple(filesystem_id)

        self.assertTrue(self.get_filesystem_by_name(self.fs_name)['name'] == self.fs_name)


def my_setUp(self):
    # connect the remote operations but otherwise...
    if config.get('simulator', False):
        self.remote_operations = SimulatorRemoteOperations(self, self.simulator)
    else:
        self.remote_operations = RealRemoteOperations(self)

    # Enable agent debugging
    self.remote_operations.enable_agent_debug(self.TEST_SERVERS)

    self.wait_until_true(self.supervisor_controlled_processes_running)
    self.initial_supervisor_controlled_process_start_times = self.get_supervisor_controlled_process_start_times()


class TestAddHost(TestCreateFilesystem):
    def setUp(self):
        my_setUp(self)

    def test_add_host(self):
        """ Test that a host and OST can be added to a filesystem"""

        volumes = self.get_usable_volumes()
        filesystem_id = self.get_filesystem_by_name(self.fs_name)['id']
        filesystem_uri = "/api/filesystem/%s/" % filesystem_id

        new_hosts = self.add_hosts([
            config['lustre_servers'][2]['address'],
            config['lustre_servers'][3]['address']
        ])

        new_volumes = [v for v in self.get_usable_volumes() if v not in volumes]
        self.assertGreaterEqual(len(new_volumes), 1)

        ost_volume = new_volumes[0]

        self.set_volume_mounts(ost_volume, new_hosts[0]['id'], new_hosts[1]['id'])

        # add the new volume to the existing filesystem
        response = self.chroma_manager.post("/api/target/", body = {
            'volume_id': ost_volume['id'],
            'kind': 'OST',
            'filesystem_id': filesystem_id
        })
        self.assertEqual(response.status_code, 202, response.text)
        target_uri = response.json['target']['resource_uri']
        create_command = response.json['command']['id']
        self.wait_for_command(self.chroma_manager, create_command)

        self.assertState(target_uri, 'mounted')
        self.assertState(filesystem_uri, 'available')

        self.assertEqual(len(self.chroma_manager.get("/api/filesystem/").json['objects'][0]['osts']), 2)


class TestExistsFilesystem(TestCreateFilesystem):
    def setUp(self):
        my_setUp(self)

    def test_exists(self):
        self.assertTrue(self.get_filesystem_by_name(self.fs_name)['name'] == self.fs_name)
        # wait for it to be available, in case we rebooted storage servers before getting here
        self.wait_until_true(lambda: self.get_filesystem_by_name(self.fs_name)['state'] == 'available')
        self._exercise_simple(self.get_filesystem_by_name(self.fs_name)['id'])
