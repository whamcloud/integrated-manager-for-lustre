import logging

from testconfig import config

from tests.integration.core.clean_cluster_testcase import CleanClusterApiTestCase
from tests.utils.http_requests import AuthorizedHttpRequests

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class ChromaIntegrationTestCase(CleanClusterApiTestCase):
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

        for host in new_hosts:
            if self.has_pacemaker(host):
                # Start lnet on each new host
                self.set_state(host['resource_uri'], 'lnet_up')

        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']

        new_hosts = [h for h in hosts if h['id'] not in [s['id'] for s in pre_existing_hosts]]
        self.assertListEqual([h['state'] for h in new_hosts], ['lnet_up'] * len(new_hosts))

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
        for host in hosts:
            result = self.remote_command(
                host['address'],
                'crm configure show'
            )
            configuration = result.stdout.read()
            self.assertRegexpMatches(
                configuration,
                "location [^\n]* %s\n" % host['nodename']
            )
            self.assertRegexpMatches(
                configuration,
                "primitive %s-" % filesystem['name']
            )
            self.assertRegexpMatches(
                configuration,
                "id=\"%s-" % filesystem['name']
            )

        return filesystem_id

    def get_shared_volumes(self, required_hosts = 2):
        """
        Return a list of shared storage volumes (have a primary and secondary node)
        """
        volumes = self.get_usable_volumes()

        ha_volumes = []
        for v in volumes:
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
        return response.json['objects']

    def verify_usable_luns_valid(self, usable_luns, num_luns_needed):
        """
        Verify a list of luns both contains the correct number of devices
        and that those devices are listed in the config as devices that
        are allowable to use. This is an extra check so that in case there
        is a bug in the chroma volume detection, we won't go wiping other
        volumes the person running the tests cares about.
        """
        # Assert meets the minimum number of devices needed for this test.
        self.assertGreaterEqual(len(usable_luns), num_luns_needed)

        # Verify no extra devices not in the config visible.
        response = self.chroma_manager.get(
            '/api/volume_node/'
        )
        self.assertTrue(response.successful, response.text)
        lun_nodes = response.json['objects']

        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        host_id_to_nodename = dict((h['id'], h['nodename']) for h in hosts)
        usable_luns_ids = [l['id'] for l in usable_luns]

        for lun_node in lun_nodes:
            if lun_node['volume_id'] in usable_luns_ids:

                # Create a list of usable device paths for the host of the
                # current lun node as listed in the config.
                host_id = lun_node['host_id']
                host_nodename = host_id_to_nodename[host_id]
                host_config = self.get_host_config(host_nodename)
                config_device_paths = host_config['device_paths']
                config_paths = [str(p) for p in config_device_paths]

                self.assertTrue(lun_node['path'] in config_paths,
                    "Path: %s Config Paths: %s" % (
                        lun_node['path'], config_device_paths)
                )

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

    def exercise_filesystem(self, client, filesystem):
        """
        Verify we can actually exercise a filesystem.

        Currently this only verifies that we can write to a filesystem as a
        sanity check that it was configured correctly.
        """
        # TODO: Expand on this. Perhaps use existing lustre client tests.
        if filesystem.get('bytes_free') == None:
            self.wait_until_true(lambda: self.get_filesystem(filesystem['id']).get('bytes_free') != None)
            filesystem = self.get_filesystem(filesystem['id'])

        self.remote_command(
            client,
            "dd if=/dev/zero of=/mnt/%s/exercisetest.dat bs=1000 count=%s" % (
                filesystem['name'],
                min((filesystem.get('bytes_free') * 0.4), 512000) / 1000
            )
        )


class AuthorizedTestCase(ChromaIntegrationTestCase):
    """Variant of ChromaIntegrationTestCase which creates an AuthorizedHttpRequests
     during setup and resets the system depending on config['reset']

    """
    def setUp(self):
        reset = config.get('reset', True)
        if reset:
            # Forcefully reset Chroma
            self.reset_cluster()

        user = config['chroma_managers'][0]['users'][0]
        self.chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
            server_http_url = config['chroma_managers'][0]['server_http_url'])

        if not reset:
            # Clean up a running Chroma instance without wiping it
            self.graceful_teardown(self.chroma_manager)
