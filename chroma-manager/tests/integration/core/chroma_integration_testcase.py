import logging

from collections import namedtuple
from testconfig import config
from tests.integration.core.api_testcase_with_test_reset import ApiTestCaseWithTestReset
from tests.integration.core.constants import LONG_TEST_TIMEOUT, INSTALL_TIMEOUT
from tests.utils.check_server_host import check_nodes_status

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class ChromaIntegrationTestCase(ApiTestCaseWithTestReset):
    """The TestCase class all chroma integration test cases should inherit form.

    This class ties together the common functionality needed in most
    integration test cases. For functionality used in a limited subset
    of tests, please see the *_testcase_mixin modules in this same directory.
    """

    def get_named_profile(self, profile_name):
        all_profiles = self.chroma_manager.get('/api/server_profile/').json['objects']
        filtered_profile = [profile for profile in all_profiles if profile['name'] == profile_name]

        assert len(filtered_profile) == 1

        return filtered_profile[0]

    def get_current_host_profile(self, host):
        """Return the profile currently running on the host."""
        return self.chroma_manager.get('/api/server_profile/?name=%s' % host['server_profile']['name']).json['objects'][0]

    def get_best_host_profile(self, address):
        """
        Return the most suitable profile for the host.

        This suitability is done using the profile validation rules.
        """
        host = next(h for h in config['lustre_servers'] if h['address'] == address)

        # If the host actually specified a profile in the configuration, then I think it's fair
        # to say that must be the best one.
        if host.get('profile'):
            return self.get_named_profile(host['profile'])

        all_profiles = self.chroma_manager.get('/api/server_profile/').json['objects']

        # Get the one for this host.
        host_validations = self.get_valid_host_validations(host).profiles

        # Merge the two so we have single list.
        for profile in all_profiles:
            profile['validations'] = host_validations[profile['name']]

        # Filter by managed.
        filtered_profile = [profile
                            for profile in all_profiles
                            if (profile['managed'] == config.get("managed", False) and
                                profile['worker'] is False and
                                profile['user_selectable'] is True)]

        # Finally get one that pass all the tests, get the whole list and validate there is only one choice
        filtered_profile = [profile
                            for profile in filtered_profile
                            if self._validation_passed(profile['validations'])]

        assert len(filtered_profile) == 1

        return filtered_profile[0]

    def _validation_passed(self, validations):
        for validation in validations:
            if validation['pass'] is False:
                return False

        return True

    HostProfiles = namedtuple("HostProfiles", ["profiles", "valid"])

    def get_host_validations(self, host):
        """
        Returns the host validations for the host passed.

        :param host: Host to get profiles for.
        :return: HostProfiles named tuple.
        """

        all_validations = self.chroma_manager.get('/api/host_profile').json['objects']

        # Return the one for this host.
        validation = next(validation['host_profiles']
                          for validation in all_validations
                          if validation['host_profiles']['address'] == host['address'])

        # Old API's don't have profiles_valid, so return work out the answer.
        if 'profiles_valid' not in validation:
            validation['profiles_valid'] = (self.chroma_manager.get('api/host/%s' % validation['host']).json['properties'] != '{}')

        return self.HostProfiles(validation['profiles'], validation['profiles_valid'])

    def get_valid_host_validations(self, host):
        """
        Returns the host validations for the host passed. The routine will wait for the validations to be valid
        before returning. If they do not become valid it will assert.

        :param host: Host to get profiles for.
        :return: HostProfiles named tuple.
        """
        self.wait_for_assert(lambda: self.assertTrue(self.get_host_validations(host).valid))

        return self.get_host_validations(host)

    def validate_hosts(self, addresses, auth_type='existing_keys_choice'):
        """Verify server checks pass for provided addresses"""
        response = self.chroma_manager.post(
            '/api/test_host/',
            body = {
                'objects': [{'address': address, 'auth_type': auth_type} for address in addresses]
            }
        )
        self.assertEqual(response.successful, True, response.text)

        for object in response.json['objects']:
            self.wait_for_command(self.chroma_manager, object['command']['id'])
            for job in object['command']['jobs']:
                response = self.chroma_manager.get(job)
                self.assertTrue(response.successful, response.text)
                host_info = response.json['step_results'].values()[0]
                address = host_info.pop('address')
                for result in host_info['status']:
                    self.assertTrue(result['value'],
                                    "Expected %s to be true for %s, but instead found %s. JSON for host: %s" %
                                    (result['name'], address, result['value'], response.json))

    def deploy_agents(self, addresses, auth_type='existing_keys_choice'):
        """Deploy the agent to the addresses provided"""
        response = self.chroma_manager.post(
            '/api/host/',
            body = {
                'objects': [{
                    'address': address,
                    'auth_type': auth_type,
                    'server_profile': '/api/server_profile/default/'
                } for address in addresses]
            }
        )
        self.assertEqual(response.successful, True, response.text)

        command_ids = []
        for object in response.json['objects']:
            host = object['command_and_host']['host']
            host_address = [host['address']][0]
            self.assertTrue(host['id'])
            self.assertTrue(host_address)
            command_ids.append(object['command_and_host']['command']['id'])

            response = self.chroma_manager.get(
                '/api/host/%s/' % host['id'],
            )
            self.assertEqual(response.successful, True, response.text)
            host = response.json
            self.assertEqual(host['address'], host_address)

            # At this point the validations should be invalid the host is added but not deployed yet.
            self.assertFalse(self.get_host_validations(host).valid)

        # Wait for deployment to complete
        self.wait_for_commands(self.chroma_manager, command_ids)

    def set_host_profiles(self, hosts):
        # Set the profile for each new host
        response = self.chroma_manager.post(
            '/api/host_profile/',
            body = {
                'objects': [{'host': h['id'], 'profile': self.get_best_host_profile(h['address'])['name']} for h in hosts]
            }
        )
        self.assertEqual(response.successful, True, response.text)
        # Wait for the server to be set up with the new server profile
        # Rather a long timeout because this may be installing packages, including Lustre and a new kernel
        command_ids = []
        for object in response.json['objects']:
            for command in object['commands']:
                command_ids.append(command['id'])

        def check_for_HYD_2849_4050():
            # Debugging added for HYD-2849, must not impact normal exception handling
            check_nodes_status(config)
            # HYD-4050: spin here so that somebody can inspect if we hit this bug
            for command_id in command_ids:
                command = self.get_json_by_uri('/api/command/%s/' % command_id)
                for job_uri in command['jobs']:
                    job = self.get_json_by_uri(job_uri)
                    job_steps = [self.get_json_by_uri(s) for s in job['steps']]
                    if job['errored']:
                        for step in job_steps:
                            if step['state'] == 'failed' and step['console'].find("is no initramfs") >= 0:
                                return True

            return False

        self._fetch_help(lambda: self.wait_for_commands(self.chroma_manager, command_ids, timeout=INSTALL_TIMEOUT),
                         ['brian.murrell@intel.com'],
                         "Waiting for developer inspection due to HYD-4050.  DO NOT ABORT THIS TEST.  NOTIFY DEVELOPER ASSIGNED TO HYD-4050.",
                         lambda: check_for_HYD_2849_4050())

    def register_simulated_hosts(self, addresses):
        host_create_command_ids = {}
        for host_address in addresses:
            host = next(h for h in config['lustre_servers'] if h['address'] == host_address)

            # POST to the /registration_token/ REST API resource to acquire
            # permission to add a server
            profile = self.get_named_profile(host['profile'])
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
            registration_result = self.simulator.register(host['fqdn'], token['secret'])
            host_create_command_ids[host_address] = registration_result['command_id']

        self.wait_for_commands(self.chroma_manager, host_create_command_ids.values())

    def add_hosts(self, addresses, auth_type='existing_keys_choice'):
        """Add a list of lustre servers to chroma and ensure lnet ends in the correct state."""
        if self.simulator:
            self.register_simulated_hosts(addresses)
        else:
            self.validate_hosts(addresses, auth_type)
            self.deploy_agents(addresses, auth_type)
            self.set_host_profiles(self.get_hosts(addresses))

        # Verify the new hosts are now in the database and in the correct state
        new_hosts = self.get_hosts(addresses)
        self.assertEqual(len(new_hosts), len(addresses), new_hosts)
        for host in new_hosts:
            # Deal with pre-3.0 versions.
            if host['state'] in ['lnet_up', 'lnet_down', 'lnet_unloaded']:
                if self.get_current_host_profile(host)['name'] == 'base_managed':
                    self.assertEqual(host['state'], 'lnet_up', host)
                else:
                    self.assertIn(host['state'], ['lnet_up', 'lnet_down', 'lnet_unloaded'], host)
            else:
                self.assertEqual(host['state'],
                                 self.get_current_host_profile(host)['initial_state'],
                                 host)

        # Make sure the agent config is flushed to disk
        self.remote_operations.sync_disks([h['address'] for h in new_hosts])

        return new_hosts

    def get_hosts(self, addresses=None):
        """
        Get the hosts from the api for all or subset of hosts.

        Keyword arguments:
        addresses: If provided, limit results to addresses specified.
        """
        response = self.chroma_manager.get('/api/host/')
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']
        if addresses:
            hosts = [h for h in hosts if h['address'] in addresses]
        return hosts

    def create_filesystem_simple(self, name = 'testfs', hsm = False):
        """
        Create the simplest possible filesystem on a single server.

        DEPRECATED - Please don't use this as it is an unsupported
        configuration. Please instead use create_filesystem_standard.
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
                'mdts': [{
                    'volume_id': mdt_volume['id'],
                    'conf_params': mdt_params
                }],
                'osts': [{
                    'volume_id': v['id'],
                    'conf_params': {}
                } for v in ost_volumes],
                'conf_params': {}
            }
        )

    @property
    def standard_filesystem_layout(self):
        if not hasattr(self, '_standard_filesystem_layout'):
            # Only want to calculate once in case ordering is nondeterministic
            hosts = self.get_hosts()
            self.assertGreaterEqual(4, len(hosts),
                "Must have added at least 4 hosts before calling standard_filesystem_layout. Found '%s'" % hosts)

            # Count how many of the reported Luns are ready for our test
            # (i.e. they have both a primary and a failover node)
            ha_volumes = self.get_shared_volumes(required_hosts = 4)
            self.assertGreaterEqual(len(ha_volumes), 4,
                "Need at least 4 ha volumes. Found '%s'" % ha_volumes)

            self._standard_filesystem_layout = {
                'mgt': {'primary_host': hosts[0], 'failover_host': hosts[1], 'volume': ha_volumes[0]},
                'mdt': {'primary_host': hosts[1], 'failover_host': hosts[0], 'volume': ha_volumes[1]},
                'ost1': {'primary_host': hosts[2], 'failover_host': hosts[3], 'volume': ha_volumes[2]},
                'ost2': {'primary_host': hosts[3], 'failover_host': hosts[2], 'volume': ha_volumes[3]},
            }
        return self._standard_filesystem_layout

    def create_filesystem_standard(self, test_servers):
        """Create a standard, basic filesystem configuration.
        One MGT, one MDT, in an active/active pair
        Two OSTs in an active/active pair"""
        # Add hosts as managed hosts
        self.assertGreaterEqual(len(test_servers), 4)
        servers = [s['address'] for s in test_servers[:4]]
        self.add_hosts(servers)

        # Set up power control for fencing -- needed to ensure that
        # failover completes. Pacemaker won't fail over the resource
        # if it can't STONITH the primary.
        if config['failover_is_configured']:
            self.configure_power_control(servers)

        # Set primary and failover mounts explicitly and check they
        # are respected
        self.set_volume_mounts(
            self.standard_filesystem_layout['mgt']['volume'],
            self.standard_filesystem_layout['mgt']['primary_host']['id'],
            self.standard_filesystem_layout['mgt']['failover_host']['id']
        )
        self.set_volume_mounts(
            self.standard_filesystem_layout['mdt']['volume'],
            self.standard_filesystem_layout['mdt']['primary_host']['id'],
            self.standard_filesystem_layout['mdt']['failover_host']['id']
        )
        self.set_volume_mounts(
            self.standard_filesystem_layout['ost1']['volume'],
            self.standard_filesystem_layout['ost1']['primary_host']['id'],
            self.standard_filesystem_layout['ost1']['failover_host']['id']
        )
        self.set_volume_mounts(
            self.standard_filesystem_layout['ost2']['volume'],
            self.standard_filesystem_layout['ost2']['primary_host']['id'],
            self.standard_filesystem_layout['ost2']['failover_host']['id']
        )

        # Create new filesystem
        return self.create_filesystem(
            {
                'name': 'testfs',
                'mgt': {'volume_id': self.standard_filesystem_layout['mgt']['volume']['id']},
                'mdts': [{'volume_id': self.standard_filesystem_layout['mdt']['volume']['id'], 'conf_params': {}}],
                'osts': [{'volume_id': v['id'], 'conf_params': {}} for v in [self.standard_filesystem_layout['ost1']['volume'], self.standard_filesystem_layout['ost2']['volume']]],
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
                    'mdts': [{'volume_id': mdt_volume['id'], 'conf_params': {}}],
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
        self.remote_operations.check_ha_config(hosts, filesystem['name'])

        return filesystem_id

    def stop_filesystem(self, filesystem_id):
        response = self.chroma_manager.put(
            '/api/filesystem/%s/' % filesystem_id,
            body = {'state': 'stopped'}
        )
        self.assertTrue(response.successful, response.text)
        self.wait_for_command(self.chroma_manager, response.json['command']['id'])

    def start_filesystem(self, filesystem_id):
        response = self.chroma_manager.put(
            '/api/filesystem/%s/' % filesystem_id,
            body = {'state': 'available'}
        )
        self.assertTrue(response.successful, response.text)
        self.wait_for_command(self.chroma_manager, response.json['command']['id'])

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

    def get_shared_volumes(self, required_hosts):
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

    def wait_for_shared_volumes(self, expected_volumes, required_hosts):
        self.wait_until_true(lambda: len(self.get_shared_volumes(required_hosts)) >= expected_volumes)

        return self.get_shared_volumes(required_hosts)

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

    def configure_power_control(self, servers):
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
            if 'host' in outlet and outlet['host'] in servers:
                hosts = self.get_list("/api/host/", args = {'limit': 0})
                try:
                    host = [h for h in hosts if h['address'] == outlet['host']][0]
                except IndexError:
                    raise RuntimeError("%s not found in /api/host/. Found '%s'" % (outlet['host'], hosts))
                new['host'] = host['resource_uri']

            try:
                obj = next(o for o in precreated_outlets if o['device'] == new['device'] and o['identifier'] == new['identifier'])
                if 'host' in new:
                    response = self.chroma_manager.patch(obj['resource_uri'],
                                                         body = {'host': new['host']})
                    self.assertEqual(response.successful, True, response.text)
                    logger.debug("Updated %s" % obj)
            except StopIteration:
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

        lnet_configuration = self.get_list("/api/lnet_configuration", args={'host__id': host["id"],
                                                                            'dehydrate__nid': True,
                                                                            'dehydrate__host': True})
        self.assertEqual(len(lnet_configuration), 1, "Expected a single lnet configuration to be returned got %s" % len(lnet_configuration))
        lnet_configuration = lnet_configuration[0]

        network_interfaces = self.get_list("/api/network_interface", args={'host__id': host["id"]})

        nids = self.get_list("/api/nid/", args={'lnet_configuration__id': lnet_configuration["id"]})

        logger.debug("Fetched Lnet info for %s" % host['fqdn'])
        logger.debug("Nid info %s" % nids)
        logger.debug("NetworkInterfaces info %s" % network_interfaces)
        logger.debug("LNetConfiguration info %s" % lnet_configuration)

        return self.LNetInfo(nids, network_interfaces, lnet_configuration, host)
