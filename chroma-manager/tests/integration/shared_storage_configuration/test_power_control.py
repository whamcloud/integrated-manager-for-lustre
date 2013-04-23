from django.utils import unittest

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class ChromaPowerControlTestCase(ChromaIntegrationTestCase):
    TESTS_NEED_POWER_CONTROL = True

    def setUp(self):
        super(ChromaPowerControlTestCase, self).setUp()

        self.power_types = {}
        self.pdu_list = []

        for power_type in config['power_control_types']:
            # Keep things simple... No need to add more outlets
            # than we have servers.
            max_outlets = len(config['lustre_servers'])
            power_type['max_outlets'] = max_outlets

            response = self.chroma_manager.post("/api/power_control_type/",
                                                body = power_type)
            self.assertTrue(response.successful, response.text)
            type_obj = response.json
            self.power_types[type_obj['name']] = type_obj

        for pdu in config['power_distribution_units']:
            import copy
            pdu_body = copy.copy(pdu)
            pdu_body['device_type'] = self.power_types[pdu['type']]['resource_uri']
            del pdu_body['type']
            response = self.chroma_manager.post("/api/power_control_device/",
                                                body = pdu_body)
            self.assertTrue(response.successful, response.text)
            pdu_obj = response.json
            self.pdu_list.append(pdu_obj)

        self.server = self.add_hosts([config['lustre_servers'][0]['address']])[0]
        # Associate the server with some PDU outlets
        for pdu in self.pdu_list:
            outlet = [o for o in pdu['outlets'] if o['identifier'] == str(1)][0]
            response = self.chroma_manager.patch(outlet['resource_uri'], body = {
                'host': self.server['resource_uri']
            })
            self.assertTrue(response.successful, response.text)

    def tearDown(self):
        # Clean out the power control types, which should ultimately
        # result in the PDU monitoring threads being reaped. This is
        # a nice teardown rather than a requirement for tests to run
        # properly.
        self.api_clear_resource('power_control_type')

        super(ChromaPowerControlTestCase, self).tearDown()


class TestPduSetup(ChromaPowerControlTestCase):
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_new_pdu_learns_outlet_states(self):
        outlets = self.get_list("/api/power_control_device_outlet/",
                args = {'limit': 0}
        )
        self.assertTrue(all([True if o['has_power'] in [True, False] else False for o in outlets]), "All outlets should be in either On or Off (not Unknown)")

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


class TestPduOperations(ChromaPowerControlTestCase):
    @unittest.skipUnless(len(config.get('power_distribution_units', [])), "requires PDUs")
    def test_off_on_operations(self):
        # Test a couple of things:
        # 1. Test that the Power(off|on) AdvertisedJobs are only advertised
        #    when they should be.
        # 2. Test that the jobs actually work.

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
        # 1. Test that the Powercycle AdvertisedJob is only advertised
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

        self.wait_until_true(lambda: self.remote_operations.host_contactable(self.server['address']))

        self.server = self.get_by_uri(self.server['resource_uri'])
        post_boot_time = self.server['boot_time']

        self.assertGreater(post_boot_time, pre_boot_time)
