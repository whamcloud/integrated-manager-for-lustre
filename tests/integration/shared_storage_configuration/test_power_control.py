from django.utils import unittest

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class ChromaPowerControlTestCase(ChromaIntegrationTestCase):
    TESTS_NEED_POWER_CONTROL = True

    def setUp(self):
        super(ChromaPowerControlTestCase, self).setUp()
        
        # Even though the tests only need 1 server, we need to add a server
        # and its HA peer in order to ensure that the peer doesn't send
        # outdated CIB data over. There is an assumption here that the
        # servers listed in the configuration are ordered by HA peer groups.
        servers = config['lustre_servers'][0:2]

        self.server = self.add_hosts([s['address'] for s in servers])[0]

        self.configure_power_control([s['address'] for s in servers])

    def all_outlets_known(self):
        outlets = self.get_list("/api/power_control_device_outlet/",
                                args = {'limit': 0})
        return all([True if o['has_power'] in [True, False] else False for o in outlets])

    def wait_for_action(self, **kwargs):
        return super(ChromaPowerControlTestCase, self).wait_for_action(self.server, **kwargs)

    def run_command(self, job):
        message = "Test {0} {1}".format(job['class_name'], self.server['address'])
        return super(ChromaPowerControlTestCase, self).run_command([job], message)


class TestPduSetup(ChromaPowerControlTestCase):
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_new_pdu_learns_outlet_states(self):
        self.wait_until_true(self.all_outlets_known)

    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    @unittest.skipUnless(config.get('power_control_types', [{}])[0].get('max_outlets', 0), "requires non-IPMI power control")
    def test_force_removed_host_disassociated_with_outlets(self):
        server_outlets = [o['resource_uri'] for o in
                          self.get_list("/api/power_control_device_outlet/")
                          if o['host'] == self.server['resource_uri']]
        self.run_command({'class_name': 'ForceRemoveHostJob', 'args': {'host_id': self.server['id']}})

        for outlet_uri in server_outlets:
            self.assertIsNone(self.get_json_by_uri(outlet_uri)['host'])

        # TODO: Check that no async stuff happened as a result of the
        # outlet disassociation (STONITH reconfiguration, etc.)

    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    @unittest.skipUnless(config.get('power_control_types', [{}])[0].get('max_outlets', 0), "requires non-IPMI power control")
    def test_removed_host_disassociated_with_outlets(self):
        server_outlets = [o['resource_uri'] for o in
                          self.get_list("/api/power_control_device_outlet/")
                          if o['host'] == self.server['resource_uri']]

        self.server['state'] = "removed"
        response = self.chroma_manager.put(self.server['resource_uri'],
                                           body = self.server)
        self.assertEquals(response.status_code, 202, response.content)
        self.wait_for_command(self.chroma_manager, response.json['command']['id'])

        with self.assertRaises(AssertionError):
            self.get_json_by_uri(self.server['resource_uri'])

        for outlet_uri in server_outlets:
            self.assertIsNone(self.get_json_by_uri(outlet_uri)['host'])


class TestHostFencingConfig(ChromaPowerControlTestCase):
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_saved_outlet_triggers_fencing_update(self):
        # NB: This test relies on the target server's HA peer having had its
        # HA config scrubbed too. If that doesn't happen, the test could
        # fail because the peer will send over an older cib DB and confound
        # this test's logic.
        server_outlets = [outlet for outlet in
                          self.get_list("/api/power_control_device_outlet/")
                          if outlet['host'] == self.server['resource_uri']]

        def host_can_be_fenced(server):
            # A host can't fence itself, but its name will show up in the
            # list of fenceable nodes.
            nodes = self.remote_operations.get_fence_nodes_list(server['address'])
            return server['fqdn'] in nodes

        # The host should initially be set up for fencing, due to the
        # associations made in setUp()
        self.wait_until_true(lambda: host_can_be_fenced(self.server))

        # Now, remove the outlet <=> server associations
        for outlet in server_outlets:
            self.chroma_manager.patch(outlet['resource_uri'],
                                      body = {'host': None})

        # After being disassociated with its outlets, the host should no
        # longer be set up for fencing
        self.wait_until_true(lambda: not host_can_be_fenced(self.server))

        # Finally, restore the outlet <=> server associations
        for outlet in server_outlets:
            self.chroma_manager.patch(outlet['resource_uri'],
                                      body = {'host': self.server['resource_uri']})

        # After being reassociated with its outlets, the host should
        # be set up for fencing again
        self.wait_until_true(lambda: host_can_be_fenced(self.server))

    @unittest.skip('disabled until https://github.com/whamcloud/integrated-manager-for-lustre/issues/315 is fixed')
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_toggled_outlet_does_not_trigger_fencing_update(self):
        def _fencing_job_count():
            return len([j for j in
                        self.get_list("/api/job/", args = {'state': "complete"})
                        if j['class_name'] == "ConfigureHostFencingJob"])

        self.wait_until_true(self.all_outlets_known)

        start_count = _fencing_job_count()

        self.run_command(self.wait_for_action(class_name='PowercycleHostJob'))

        end_count = _fencing_job_count()

        self.assertEqual(start_count, end_count)

        # Not strictly part of the test, but avoids AWOL node failures
        self.wait_until_true(lambda: self.remote_operations.host_contactable(self.server['address']))


class TestPduOperations(ChromaPowerControlTestCase):
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_off_on_operations(self):
        # Test a couple of things:
        # 1. Test that the Power(off|on) AdvertisedJobs are only advertised
        #    when they should be.
        # 2. Test that the jobs actually work.

        self.wait_until_true(self.all_outlets_known)

        poweroff_job = self.wait_for_action(class_name='PoweroffHostJob')

        # FIXME: When HYD-2071 lands, this will be done implicitly by the API.
        self.remote_operations.set_node_standby(self.server)

        self.run_command(poweroff_job)

        self.wait_until_true(lambda: not self.remote_operations.host_contactable(self.server['address']))

        self.run_command(self.wait_for_action(class_name='PoweronHostJob'))

        self.wait_until_true(lambda: self.remote_operations.host_contactable(self.server['address']))

        # HYD-2071
        self.remote_operations.set_node_online(self.server)

    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_powercycle_operation(self):
        # Test a couple of things:
        # 1. Test that the Powercycle AdvertisedJob is advertised
        #    when it should be.
        # 2. Test that the job actually works.

        # Refresh the server so we get an accurate list of available jobs.
        self.server = self.get_json_by_uri(self.server['resource_uri'])
        pre_boot_time = self.server['boot_time']

        self.run_command(self.wait_for_action(class_name='PowercycleHostJob'))

        def boot_time_is_newer():
            server = self.get_json_by_uri(self.server['resource_uri'])
            post_boot_time = server['boot_time']
            return post_boot_time > pre_boot_time

        self.wait_until_true(boot_time_is_newer)
