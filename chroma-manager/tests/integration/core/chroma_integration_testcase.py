import logging

from collections import namedtuple
from testconfig import config
from tests.integration.core.api_testcase_with_test_reset import ApiTestCaseWithTestReset
from tests.integration.core.constants import LONG_TEST_TIMEOUT

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class ChromaIntegrationTestCase(ApiTestCaseWithTestReset):
    """
    The TestCase class all chroma integration test cases should inherit form.

    This class ties together the common functionality needed in most
    integration test cases. For functionality used in a limited subset
    of tests, please see the *_testcase_mixin modules in this same directory.
    """

    def get_host_profile(self, address):
        try:
            host = [h for h in config['lustre_servers']
                    if h['address'] == address][0]
            response = self.chroma_manager.get("/api/server_profile/?name=%s" % host['profile'])
            return response.json['objects'][0]
        except KeyError:
            if config.get('managed'):
                response = self.chroma_manager.get("/api/server_profile/?managed=true&worker=false")
            else:
                response = self.chroma_manager.get("/api/server_profile/?managed=false")
            return response.json['objects'][0]
        except IndexError:
            raise RuntimeError("No host in config with address %s" % address)

    def add_hosts(self, addresses):
        """
        Add a list of lustre servers to chroma and ensure lnet is started.
        """

        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        pre_existing_hosts = response.json['objects']

        host_create_command_ids = {}
        for host_address in addresses:
            profile = self.get_host_profile(host_address)

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
                    body={
                        'credits': 1,
                        'profile': profile['resource_uri']
                    }
                )
                self.assertTrue(response.successful, response.text)
                token = response.json

                # Pass our token to the simulator to register a server
                registration_result = self.simulator.register(fqdn, token['secret'])
                host_create_command_ids[host_address] = registration_result['command_id']
            else:
                response = self.chroma_manager.post(
                    '/api/test_host/',
                    body = {
                        'address': host_address,
                        'server_profile': profile['resource_uri']       # Not required for current versions - but needed for old versions in upgrade testing
                    }
                )
                self.assertEqual(response.successful, True, response.text)

                # If the manager return some commands then this is a 2.2 or later manager (should be a better way of knowing versions!
                if 'objects' in response.json:
                    command_id = response.json['objects'][0]['id']

                    self.wait_for_command(self.chroma_manager, command_id, timeout=1200)

                    results = {}

                    for job in response.json['objects'][0]['jobs']:
                        response = self.chroma_manager.get(job)
                        self.assertEqual(response.successful, True, response.text)

                        results = dict(results.items() + response.json['step_results'].items())
                else:
                    results = {"": response.json}

                for result in results.values():
                    if not config.get('ssh_config', None):
                        self.assertTrue(result['ping'])
                        self.assertTrue(result['resolve'])

                    self.assertTrue(result['auth'])
                    self.assertTrue(result['reverse_ping'])
                    self.assertTrue(result['reverse_resolve'])

                response = self.chroma_manager.post(
                    '/api/host/',
                    body={
                        'address': host_address,
                        'server_profile': profile['resource_uri']
                    }
                )
                self.assertEqual(response.successful, True, response.text)
                host_id = response.json['host']['id']
                host_create_command_ids[host_address] = response.json['command']['id']
                self.assertTrue(host_id)

                response = self.chroma_manager.get(
                    '/api/host/%s/' % host_id,
                )
                self.assertEqual(response.successful, True, response.text)
                host = response.json
                self.assertEqual(host['address'], host_address)

        # Wait for the host setup to complete
        # Rather a long timeout because this may include installing Lustre and rebooting
        # Capture the rpm state if host setup fails
        for host_address, command_id in host_create_command_ids.items():
            try:
                self.wait_for_command(self.chroma_manager, command_id, timeout=1200)
            except AssertionError:
                # Debugging added for HYD-2849, must not impact normal exception handling
                if not hasattr(self, 'simulator'):
                    for cmd in ('rpm -qa', 'rpm -Va'):
                        print 'run:', cmd
                        result = self.remote_command(host_address, cmd, expected_return_code=None)
                        print 'exit_status:', result.exit_status
                        print 'stdout', result.stdout.read()
                raise

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

        # Make sure the agent config is flushed to disk
        self.remote_operations.sync_disks(new_hosts)

        return new_hosts

    def create_filesystem_simple(self, name = 'testfs', hsm = False):
        """
        Create the simplest possible filesystem on a single server.
        """
        self.add_hosts([self.TEST_SERVERS[0]['address']])

        def at_least_3_volumes():
            return len(self.get_usable_volumes()) >= 3

        self.wait_until_true(lambda: at_least_3_volumes())

        ha_volumes = self.get_usable_volumes()

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volumes = [ha_volumes[2]]
        mdt_params = {}
        if hsm:
            mdt_params['mdt.hsm_control'] = "enabled"
        return self.create_filesystem(
            {
                'name': name,
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': mdt_params
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

        self.wait_for_command(
            self.chroma_manager,
            command_id,
            verify_successful=verify_successful,
            timeout = LONG_TEST_TIMEOUT
        )

        response = self.chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        # Verify mgs and fs targets in pacemaker config for hosts
        self.remote_operations.check_ha_config(hosts, filesystem)

        return filesystem_id

    def create_client_mount(self, host_uri, filesystem_uri, mountpoint):
        # Normally this is done as part of copytool creation, but we need
        # to give the test harness some way of doing it via API.
        response = self.chroma_manager.post(
            '/api/client_mount/',
            body = dict(host = host_uri,
                        filesystem = filesystem_uri, mountpoint = mountpoint)
        )
        self.assertTrue(response.successful, response.text)
        return response.json['client_mount']

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

    def create_power_control_type(self, body):
        response = self.chroma_manager.post("/api/power_control_type/",
                                            body = body)
        self.assertTrue(response.successful, response.text)
        return response.json

    def create_power_control_device(self, body):
        response = self.chroma_manager.post("/api/power_control_device/",
                                            body = body)
        self.assertTrue(response.successful, response.text)
        return response.json

    def create_power_control_device_outlet(self, body):
        response = self.chroma_manager.post("/api/power_control_device_outlet/",
                                            body = body)
        self.assertTrue(response.successful, response.text)
        return response.json

    def configure_power_control(self):
        if not config.get('power_control_types', False):
            return

        logger.info("Configuring power control")

        # clear out existing power stuff
        self.api_clear_resource('power_control_type')
        # Ensure that this stuff gets cleaned up, no matter what
        self.addCleanup(self.api_clear_resource, 'power_control_type')

        power_types = {}
        for power_type in config['power_control_types']:
            obj = self.create_power_control_type(power_type)
            power_types[obj['name']] = obj
            logger.debug("Created %s" % obj['resource_uri'])

        power_devices = {}
        for pdu in config['power_distribution_units']:
            body = pdu.copy()
            try:
                body['device_type'] = power_types[pdu['type']]['resource_uri']
            except KeyError:
                logger.debug(pdu['type'])
                logger.debug(power_types)
            del body['type']
            obj = self.create_power_control_device(body)
            power_devices["%s:%s" % (obj['address'], obj['port'])] = obj
            logger.debug("Created %s" % obj['resource_uri'])

        precreated_outlets = self.get_list("/api/power_control_device_outlet/", args = {'limit': 0})

        for outlet in config['pdu_outlets']:
            new = {'identifier': outlet['identifier'],
                   'device': power_devices[outlet['pdu']]['resource_uri']}
            if 'host' in outlet and outlet['host'] in [h['address'] for h in self.TEST_SERVERS]:
                hosts = self.get_list("/api/host/", args = {'limit': 0})
                try:
                    host = [h for h in hosts if h['address'] == outlet['host']][0]
                except IndexError:
                    raise RuntimeError("%s not found in /api/host/" % outlet['host'])
                new['host'] = host['resource_uri']

            try:
                obj = [o for o in precreated_outlets if o['device'] == new['device'] and o['identifier'] == new['identifier']][0]
                if 'host' in new:
                    response = self.chroma_manager.patch(obj['resource_uri'],
                                                         body = {'host': new['host']})
                    self.assertEqual(response.successful, True, response.text)
                    logger.debug("Updated %s" % obj)
            except IndexError:
                obj = self.create_power_control_device_outlet(new)
                logger.debug("Created %s" % obj)

    LNetInfo = namedtuple("LNetInfo", ("nids", "network_interfaces", "lnet_configuration", "host"))

    def _get_lnet_info(self, host):
        '''
        :return: Returns a named tuple of network and lnet configuration or None if lnet configuration is not provided
                 by the version of the manager
        '''

        # Check that the version of the manager running supports lnet_configuration.
        if ("lnet_configuration" not in self.chroma_manager_api):
            return None

        # We fetch the host again so that it's state is updated.
        hosts = self.get_list("/api/host/", args={'fqdn': host['fqdn']})
        self.assertEqual(len(hosts), 1, "Expected a single host to be returned got %s" % len(hosts))
        host = hosts[0]

        lnet_configuration = self.get_list("/api/lnet_configuration", args={'host__id': host["id"]})
        self.assertEqual(len(lnet_configuration), 1, "Expected a single lnet configuration to be returned got %s" % len(lnet_configuration))
        lnet_configuration = lnet_configuration[0]

        network_interfaces = self.get_list("/api/network_interface", args={'host__id': host["id"]})

        nids = self.get_list("/api/nid/", args={'lnet_configuration__id': lnet_configuration["id"]})

        logger.debug("Fetched Lnet info for %s" % host['fqdn'])
        logger.debug("Nid info %s" % nids)
        logger.debug("NetworkInterfaces info %s" % network_interfaces)
        logger.debug("LNetConfiguration info %s" % lnet_configuration)

        return self.LNetInfo(nids, network_interfaces, lnet_configuration, host)
