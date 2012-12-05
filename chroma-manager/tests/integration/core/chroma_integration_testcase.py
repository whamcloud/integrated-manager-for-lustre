
import logging

from testconfig import config
from tests.integration.core.api_testcase import ApiTestCase
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.remote_operations import  SimulatorRemoteOperations, RealRemoteOperations
from chroma_core.services.cluster_sim.simulator import ClusterSimulator


logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class ChromaIntegrationTestCase(ApiTestCase):
    """
    The TestCase class all chroma integration test cases should inherit form.

    This class ties together the common functionality needed in most
    integration test cases. For functionality used in a limited subset
    of tests, please see the *_testcase_mixin modules in this same directory.
    """

    def setUp(self):
        if config.get('simulator', False):
            state_path = 'simulator_state_%s.%s' % (self.__class__.__name__, self._testMethodName)

            self.simulator = ClusterSimulator(4, state_path, config['chroma_managers'][0]['server_http_url'])
            self.remote_operations = SimulatorRemoteOperations(self.simulator)
        else:
            self.remote_operations = RealRemoteOperations(self)

        reset = config.get('reset', True)
        if reset:
            self.reset_cluster()
        else:
            # Reset the manager via the API
            self.remote_operations.unmount_clients()
            self.api_force_clear()
            self.remote_operations.clear_ha()

    def tearDown(self):
        if hasattr(self, 'simulator'):
            self.simulator.stop()
            self.simulator.join()

    def reset_cluster(self):
        """
        Will fully wipe a test cluster:
          - dropping and recreating the chroma manager database
          - unmounting any lustre filesystems from the clients
          - unconfiguring any chroma targets in pacemaker
        """
        self.remote_operations.unmount_clients()
        self.reset_chroma_manager_db()
        self.remote_operations.clear_ha()

    def add_hosts(self, addresses):
        """
        Add a list of lustre servers to chroma and ensure lnet is started.
        """
        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        pre_existing_hosts = response.json['objects']

        host_create_command_ids = []
        for host_address in addresses:
            if hasattr(self, 'simulator'):
                # FIXME: requiring config to have same address and fqdn (address
                # is not meaningful to the simulator)
                registration_result = self.simulator.register(host_address)
                self.simulator.start_server(host_address)
                host_create_command_ids.append(registration_result['command_id'])
            else:
                response = self.chroma_manager.post(
                    '/api/test_host/',
                    body = {'address': host_address}
                )
                self.assertEqual(response.successful, True, response.text)
                self.assertTrue(response.json['agent'])
                self.assertTrue(response.json['ping'])
                self.assertTrue(response.json['resolve'])
                self.assertTrue(response.json['reverse_ping'])
                self.assertTrue(response.json['reverse_resolve'])

                response = self.chroma_manager.post(
                    '/api/host/',
                    body = {'address': host_address}
                )
                self.assertEqual(response.successful, True, response.text)
                host_id = response.json['host']['id']
                host_create_command_ids.append(response.json['command']['id'])
                self.assertTrue(host_id)

                response = self.chroma_manager.get(
                    '/api/host/%s/' % host_id,
                )
                self.assertEqual(response.successful, True, response.text)
                host = response.json
                self.assertEqual(host['address'], host_address)

        # Wait for the host setup and device discovery to complete
        self.wait_for_commands(self.chroma_manager, host_create_command_ids)

        # Verify there are now n hosts in the database.
        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']
        self.assertEqual(len(addresses), len(hosts) - len(pre_existing_hosts))

        new_hosts = [h for h in hosts if h['id'] not in [s['id'] for s in pre_existing_hosts]]

        for host in new_hosts:
            self.assertIn(host['state'], ['lnet_up', 'lnet_down', 'lnet_unloaded'])

        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']

        new_hosts = [h for h in hosts if h['id'] not in [s['id'] for s in pre_existing_hosts]]

        return new_hosts

    def create_filesystem_simple(self, name = 'testfs'):
        """
        Create the simplest possible filesystem on a single server.
        """
        self.add_hosts([config['lustre_servers'][0]['address']])

        ha_volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(ha_volumes), 3)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volumes = [ha_volumes[2]]
        return self.create_filesystem(
                {
                'name': name,
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

    def create_filesystem(self, filesystem, verify_successful = True):
        """
        Specify a filesystem to be created by chroma.

        Example usage:
            filesystem_id = self.create_filesystem(
                {
                    'name': 'testfs',
                    'mgt': {'volume_id': mgt_volume['id']},
                    'mdt': {'volume_id': mdt_volume['id'], 'conf_params': {}},
                    'osts': [{'volume_id': v['id'], 'conf_params': {}} for v in [ost_volume_1, ost_volume_2]],
                    'conf_params': {}
                }
            )
        """
        response = self.chroma_manager.post(
            '/api/filesystem/',
            body = filesystem
        )

        self.assertTrue(response.successful, response.text)
        filesystem_id = response.json['filesystem']['id']
        command_id = response.json['command']['id']

        self.wait_for_command(self.chroma_manager, command_id,
            verify_successful=verify_successful)

        response = self.chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        # Verify mgs and fs targets in pacemaker config for hosts
        self.remote_operations.check_ha_config(hosts, filesystem)

        return filesystem_id

    def get_shared_volumes(self, required_hosts = 2):
        """
        Return a list of shared storage volumes (have a primary and secondary node)
        """
        volumes = self.get_usable_volumes()

        ha_volumes = []
        for v in volumes:
            print v
            has_primary = len([node for node in v['volume_nodes'] if node['primary']]) == 1
            has_two = len([node for node in v['volume_nodes'] if node['use']]) >= 2
            accessible_enough = len(v['volume_nodes']) >= required_hosts
            if has_primary and has_two and accessible_enough:
                ha_volumes.append(v)

        return ha_volumes

    def get_usable_volumes(self):
        response = self.chroma_manager.get(
            '/api/volume/',
            params = {'category': 'usable', 'limit': 0}
        )
        self.assertEqual(response.successful, True, response.text)
        volumes = response.json['objects']
        return self.filter_for_permitted_volumes(volumes)

    def filter_for_permitted_volumes(self, volumes):
        """
        Take a list of volumes and return the members of the list that are also in the config.
        This is an extra check so that if there is a bug in the chroma volume detection,
        we won't go wiping other volumes the person running the tests cares about.
        """
        permitted_volumes = []
        for volume in volumes:
            for volume_node in volume['volume_nodes']:
                host = self.chroma_manager.get(volume_node['host']).json
                host_config = self.get_host_config(host['nodename'])
                if host_config:
                    if volume_node['path'] in host_config['device_paths']:
                        permitted_volumes.append(volume)
                        break
                    else:
                        logger.warning("%s not in %s" % (volume_node['path'], host_config['device_paths']))
                else:
                    logger.warning("No host config for '%s'" % host['nodename'])
        return permitted_volumes

    def set_volume_mounts(self, volume, primary_host_id, secondary_host_id):
        primary_volume_node_id = None
        secondary_volume_node_id = None
        for node in volume['volume_nodes']:
            if node['host_id'] == int(primary_host_id):
                primary_volume_node_id = node['id']
            elif node['host_id'] == int(secondary_host_id):
                secondary_volume_node_id = node['id']

        self.assertTrue(primary_volume_node_id, volume)
        self.assertTrue(secondary_volume_node_id, volume)

        response = self.chroma_manager.put(
            "/api/volume/%s/" % volume['id'],
            body = {
                "id": volume['id'],
                "nodes": [
                    {
                        "id": secondary_volume_node_id,
                        "primary": False,
                        "use": True,
                    },
                    {
                        "id": primary_volume_node_id,
                        "primary": True,
                        "use": True,
                    }
                ]
            }
        )
        self.assertTrue(response.successful, response.text)

    def verify_volume_mounts(self, volume, expected_primary_host_id, expected_secondary_host_id):
        """
        Verify that a given volume has the expected values for its primary and secondary hosts.
        """
        for node in volume['volume_nodes']:
            if node['primary']:
                self.assertEqual(node['host_id'], int(expected_primary_host_id))
            elif node['use']:
                self.assertEqual(node['host_id'], int(expected_secondary_host_id))

    def reset_chroma_manager_db(self):
        for chroma_manager in config['chroma_managers']:
            superuser = [u for u in chroma_manager['users'] if u['super']][0]

            # Stop all chroma manager services
            result = self.remote_command(
                chroma_manager['address'],
                'chroma-config stop',
                expected_return_code = None
            )
            if not result.exit_status == 0:
                logger.warn("chroma-config stop failed: rc:%s out:'%s' err:'%s'" % (result.exit_status, result.stdout.read(), result.stderr.read()))

            # Wait for all of the chroma manager services to stop
            running_time = 0
            services = ['chroma-supervisor']
            while services and running_time < TEST_TIMEOUT:
                for service in services:
                    result = self.remote_command(
                        chroma_manager['address'],
                        'service %s status' % service,
                        expected_return_code = None
                    )
                    if result.exit_status == 3:
                        services.remove(service)
                running_time += 1
            self.assertEqual(services, [], "Not all services were stopped by chroma-config before timeout: %s" % services)

            # Drop the database to start from a clean state.
            self.remote_command(
                chroma_manager['address'],
                'echo "drop database chroma; create database chroma;" | mysql -u root'
            )

            # Run chroma-config setup to recreate the database and start the chroma manager.
            result = self.remote_command(
                chroma_manager['address'],
                "chroma-config setup %s %s localhost &> config_setup.log" % (superuser['username'], superuser['password']),
                expected_return_code = None
            )
            chroma_config_exit_status = result.exit_status
            if not chroma_config_exit_status == 0:
                result = self.remote_command(
                    chroma_manager['address'],
                    "cat config_setup.log"
                )
                self.assertEqual(0, chroma_config_exit_status, "chroma-config setup failed: '%s'" % result.stdout.read())

    def api_force_clear(self):
        """
        Clears the Chroma instance via the API (by issuing ForceRemoveHost
        commands) -- note that this will *not* unconfigure storage servers or
        remove corosync resources: do that separately.
        """

        response = self.chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                command = self.chroma_manager.post("/api/command/", body = {
                    'jobs': [{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host['id']}}],
                    'message': "Test force remove hosts"
                }).json
                remove_host_command_ids.append(command['id'])

            self.wait_for_commands(self.chroma_manager, remove_host_command_ids)

    def graceful_teardown(self, chroma_manager):
        """
        Removes all filesystems, MGSs, and hosts from chroma via the api.  This is
        not guaranteed to work, and should be done at the end of tests in order to
        verify that the chroma manager instance was in a nice state, rather than
        in setUp/tearDown hooks to ensure a clean system.
        """
        response = chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        self.assertEqual(response.status_code, 200)
        filesystems = response.json['objects']

        self.remote_operations.unmount_clients()

        if len(filesystems) > 0:
            # Remove filesystems
            remove_filesystem_command_ids = []
            for filesystem in filesystems:
                response = chroma_manager.delete(filesystem['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_filesystem_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_filesystem_command_ids)

        # Remove MGT
        response = chroma_manager.get(
            '/api/target/',
            params = {'kind': 'MGT', 'limit': 0}
        )
        mgts = response.json['objects']

        if len(mgts) > 0:
            remove_mgt_command_ids = []
            for mgt in mgts:
                response = chroma_manager.delete(mgt['resource_uri'])
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_mgt_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_mgt_command_ids)

        # Remove hosts
        response = chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                response = chroma_manager.delete(host['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_host_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_host_command_ids)

        self.assertDatabaseClear()

    def assertDatabaseClear(self, chroma_manager = None):
        """
        Checks that the chroma manager API is now clear of filesystems, targets,
        hosts and volumes.
        """

        if chroma_manager is None:
            chroma_manager = self.chroma_manager

        # Verify there are zero filesystems
        response = chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        filesystems = response.json['objects']
        self.assertEqual(0, len(filesystems))

        # Verify there are zero mgts
        response = chroma_manager.get(
            '/api/target/',
            params = {'kind': 'MGT'}
        )
        self.assertTrue(response.successful, response.text)
        mgts = response.json['objects']
        self.assertEqual(0, len(mgts))

        # Verify there are now zero hosts in the database.
        response = chroma_manager.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']
        self.assertEqual(0, len(hosts))

        # Verify there are now zero volumes in the database.
        response = chroma_manager.get(
            '/api/volume/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        volumes = response.json['objects']
        self.assertEqual(0, len(volumes))

    def reset_accounts(self, chroma_manager):
        """Remove any user accounts which are not in the config (such as
        those left hanging by tests)"""

        configured_usernames = [u['username'] for u in config['chroma_managers'][0]['users']]

        response = chroma_manager.get('/api/user/', data = {'limit': 0})
        self.assertEqual(response.status_code, 200)
        for user in response.json['objects']:
            if not user['username'] in configured_usernames:
                chroma_manager.delete(user['resource_uri'])
