from django.utils import unittest

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class ChromaPowerControlTestCase(ChromaIntegrationTestCase):
    TESTS_NEED_POWER_CONTROL = True
    TEST_SERVERS = [config['lustre_servers'][0]]

    def setUp(self):
        self.test_server_addresses = [h['address'] for h in self.TEST_SERVERS]

        super(ChromaPowerControlTestCase, self).setUp()

        self.server = self.add_hosts([self.TEST_SERVERS[0]['address']])[0]

        self.configure_power_control()

        # This should help to avoid any lingering threads
        self.addCleanup(lambda: self.api_clear_resource('power_control_type'))

    def all_outlets_known(self):
        outlets = self.get_list("/api/power_control_device_outlet/",
                                args = {'limit': 0})
        return all([True if o['has_power'] in [True, False] else False for o in outlets])


class TestPduSetup(ChromaPowerControlTestCase):
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_new_pdu_learns_outlet_states(self):
        self.wait_until_true(self.all_outlets_known)

    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_force_removed_host_disassociated_with_outlets(self):
        server_outlets = [o['resource_uri'] for o in
                          self.get_list("/api/power_control_device_outlet/")
                          if o['host'] == self.server['resource_uri']]
        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'ForceRemoveHostJob',
                      'args': {'host_id': self.server['id']}}],
            'message': "Test forced remove of %s" % self.server['fqdn']
        }).json
        self.wait_for_command(self.chroma_manager, command['id'])

        for outlet_uri in server_outlets:
            outlet = self.get_by_uri(outlet_uri)
            self.assertEqual(outlet['host'], None)

        # TODO: Check that no async stuff happened as a result of the
        # outlet disassociation (STONITH reconfiguration, etc.)

    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
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
            self.get_by_uri(self.server['resource_uri'])

        for outlet_uri in server_outlets:
            outlet = self.get_by_uri(outlet_uri)
            self.assertEqual(outlet['host'], None)

    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_saved_outlet_triggers_fencing_update(self):
        server_outlets = [o['resource_uri'] for o in
                          self.get_list("/api/power_control_device_outlet/")
                          if o['host'] == self.server['resource_uri']]

        def host_needs_fence_reconfig():
            return self.get_by_uri(self.server['resource_uri'])['needs_fence_reconfiguration']

        # Starting out, we shouldn't need to reconfigure fencing on this host.
        # ... But we might need to wait for things to settle after setup.
        self.wait_until_true(lambda: not host_needs_fence_reconfig())

        for outlet in server_outlets:
            self.chroma_manager.patch(outlet,
                                      body = {'host': None})

        # After being disassociated with some outlets, the host should now
        # need to be reconfigured.
        self.wait_until_true(host_needs_fence_reconfig)

        # After a while, the fencing reconfig job will complete and mark
        # the host as not needing reconfiguration.
        self.wait_until_true(lambda: not host_needs_fence_reconfig())


class TestPduOperations(ChromaPowerControlTestCase):
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_off_on_operations(self):
        # Test a couple of things:
        # 1. Test that the Power(off|on) AdvertisedJobs are only advertised
        #    when they should be.
        # 2. Test that the jobs actually work.

        self.wait_until_true(self.all_outlets_known)

        # Refresh the server so we get an accurate list of available jobs.
        self.server = self.get_by_uri(self.server['resource_uri'])

        poweroff_job = None
        for job in self.server['available_jobs']:
            if job['class_name'] == 'PoweroffHostJob':
                poweroff_job = job
                break

        assert poweroff_job, "PoweroffHostJob was not advertised in %s" % [job['class_name'] for job in self.server['available_jobs']]
        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [poweroff_job],
            'message': "Test PoweroffHostJob (%s)" % self.server['address']
        }).json

        self.wait_for_command(self.chroma_manager, command['id'])

        self.wait_until_true(lambda: not self.remote_operations.host_contactable(self.server['address']))

        # Refresh the server so we get an accurate list of available jobs.
        self.server = self.get_by_uri(self.server['resource_uri'])

        poweron_job = None
        for job in self.server['available_jobs']:
            if job['class_name'] == 'PoweronHostJob':
                poweron_job = job
                break

        assert poweron_job, "PoweronHostJob was not advertised in %s" % [job['class_name'] for job in self.server['available_jobs']]
        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [poweron_job],
            'message': "Test PoweronHostJob (%s)" % self.server['address']
        }).json

        self.wait_for_command(self.chroma_manager, command['id'])

        self.wait_until_true(lambda: self.remote_operations.host_contactable(self.server['address']))

    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_powercycle_operation(self):
        # Test a couple of things:
        # 1. Test that the Powercycle AdvertisedJob is advertised
        #    when it should be.
        # 2. Test that the job actually works.

        # Refresh the server so we get an accurate list of available jobs.
        self.server = self.get_by_uri(self.server['resource_uri'])
        pre_boot_time = self.server['boot_time']

        powercycle_job = None
        for job in self.server['available_jobs']:
            if job['class_name'] == 'PowercycleHostJob':
                powercycle_job = job
                break

        assert powercycle_job, "PowercycleHostJob was not advertised in %s" % [job['class_name'] for job in self.server['available_jobs']]
        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [powercycle_job],
            'message': "Test PowercycleHostJob (%s)" % self.server['address']
        }).json

        self.wait_for_command(self.chroma_manager, command['id'])

        def boot_time_is_newer():
            server = self.get_by_uri(self.server['resource_uri'])
            post_boot_time = server['boot_time']
            return post_boot_time > pre_boot_time

        self.wait_until_true(boot_time_is_newer)
