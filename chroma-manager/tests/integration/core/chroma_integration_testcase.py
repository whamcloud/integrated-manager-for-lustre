import logging

from testconfig import config
from tests.integration.core.api_testcase_with_test_reset import ApiTestCaseWithTestReset


logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class ChromaIntegrationTestCase(ApiTestCaseWithTestReset):
    """
    The TestCase class all chroma integration test cases should inherit form.

    This class ties together the common functionality needed in most
    integration test cases. For functionality used in a limited subset
    of tests, please see the *_testcase_mixin modules in this same directory.
    """

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
                # FIXME: should look up fqdn from address rather than
                # assuming they are the same.  note that address is
                # not meaningful to the simulator ('address' is shorthand
                # for 'ssh address').
                fqdn = host_address

                # POST to the /registration_token/ REST API resource to acquire
                # permission to add a server
                response = self.chroma_manager.post(
                    '/api/registration_token/',
                    body = {'credits': 1}
                )
                self.assertTrue(response.successful, response.text)
                token = response.json

                # Pass our token to the simulator to register a server
                registration_result = self.simulator.register(fqdn, token['secret'])
                host_create_command_ids.append(registration_result['command_id'])
            else:
                response = self.chroma_manager.post(
                    '/api/test_host/',
                    body = {'address': host_address}
                )
                self.assertEqual(response.successful, True, response.text)
                self.assertTrue(response.json['agent'])
                self.assertTrue(response.json['ping'])
                self.assertTrue(response.json['auth'])
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
