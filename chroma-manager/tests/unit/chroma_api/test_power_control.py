
import mock
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helper import synthetic_host, log


class PowerControlResourceTestCase(ChromaApiTestCase):
    def setUp(self):
        super(PowerControlResourceTestCase, self).setUp()

        from chroma_core.services.power_control.rpc import PowerControlRpc
        from chroma_core.services.power_control.manager import PowerControlManager
        PowerControlManager.query_device_outlets = mock.Mock()

        manager = PowerControlManager()

        def rpc_local(fn_name, *args, **kwargs):
            retval = getattr(manager, fn_name)(*args, **kwargs)
            log.info("rpc_local: %s(%s %s) -> %s" % (fn_name, args, kwargs, retval))
            return retval

        PowerControlRpc._call = mock.Mock(side_effect = rpc_local)

    def _create_resource(self, create_uri, **kwargs):
        response = self.api_client.post(create_uri, data = kwargs)
        try:
            self.assertHttpCreated(response)
            return self.deserialize(response)
        except AssertionError:
            raise AssertionError("response = %s:%s" % (response.status_code, self.deserialize(response)))

    def _create_power_type(self, **kwargs):
        return self._create_resource("/api/power_control_type/", **kwargs)

    def _create_power_device(self, **kwargs):
        return self._create_resource("/api/power_control_device/", **kwargs)

    def _create_power_outlet(self, **kwargs):
        return self._create_resource("/api/power_control_device_outlet/", **kwargs)


class BasicPowerControlResourceTests(PowerControlResourceTestCase):
    def test_creation_with_inherited_values(self):
        self._create_power_type(agent = 'fence_apc',
                                make = 'FAKE',
                                model = 'FAKE',
                                max_outlets = 8,
                                default_username = 'apc',
                                default_password = 'apc',
                                default_options = 'foo=x')

        power_type = self.api_get_list("/api/power_control_type/")[0]
        self._create_power_device(device_type = power_type['resource_uri'],
                                  address = '1.2.3.4')

        new_pdu = self.api_get_list("/api/power_control_device/")[0]
        self.assertEqual(new_pdu['name'], new_pdu['address'])
        self.assertEqual(new_pdu['port'], power_type['default_port'])
        self.assertEqual(new_pdu['username'], power_type['default_username'])
        self.assertEqual(new_pdu['password'], power_type['default_password'])
        self.assertEqual(new_pdu['options'], power_type['default_options'])

    def test_creation_with_all_values_supplied(self):
        self._create_power_type(agent = 'fence_apc',
                                make = 'FAKE',
                                model = 'FAKE',
                                max_outlets = 8,
                                default_username = 'apc',
                                default_password = 'apc',
                                default_options = "foo=x")

        power_type = self.api_get_list("/api/power_control_type/")[0]
        self._create_power_device(device_type = power_type['resource_uri'],
                                  name = 'foopdu',
                                  address = '1.2.3.4',
                                  port = 2300,
                                  username = 'super',
                                  password = 's3kr3t',
                                  options = "foo=y")

        new_pdu = self.api_get_list("/api/power_control_device/")[0]
        self.assertEqual(new_pdu['name'], 'foopdu')
        self.assertEqual(new_pdu['port'], 2300)
        self.assertEqual(new_pdu['username'], 'super')
        self.assertEqual(new_pdu['password'], 's3kr3t')
        self.assertEqual(new_pdu['options'], 'foo=y')


class PowerControlResourceTests(PowerControlResourceTestCase):
    def setUp(self):
        super(PowerControlResourceTests, self).setUp()

        self.max_outlets = 8

        self._create_power_type(agent = 'fence_apc',
                                default_username = 'apc',
                                default_password = 'apc',
                                max_outlets = self.max_outlets)
        self.pdu_type = self.api_get_list("/api/power_control_type/")[0]
        self._create_power_device(device_type = self.pdu_type['resource_uri'],
                                  address = '1.2.3.4')
        self.pdu = self.api_get_list("/api/power_control_device/")[0]

    def test_pdu_devices_prepopulate_outlets(self):
        outlets = self.api_get(self.pdu['resource_uri'])['outlets']
        pdu_count = len(self.api_get_list("/api/power_control_device/"))
        self.assertEqual(len(outlets), self.max_outlets * pdu_count)

    def test_adding_more_than_max_outlets(self):
        with self.assertRaisesRegexp(AssertionError, '.*max.*outlets.*'):
            self._create_power_outlet(device = self.pdu['resource_uri'],
                                      identifier = self.max_outlets + 1)

        outlets = self.api_get(self.pdu['resource_uri'])['outlets']
        self.assertEqual(len(outlets), self.max_outlets)

    @mock.patch('chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.notify')
    def test_associating_outlets_with_hosts(self, notify):
        synthetic_host(address = 'foo')
        host = self.api_get_list("/api/host/")[0]

        outlet = self.api_get_list("/api/power_control_device_outlet/")[0]

        self.api_patch_attributes(outlet['resource_uri'], {
            'host': host['resource_uri']
        })

        outlet = self.api_get(outlet['resource_uri'])
        self.assertEqual(outlet['host'], host['resource_uri'])

        self.assertTrue(notify.called)

    def test_deleting_devices_deletes_outlets(self):
        pre_count = len(self.api_get_list("/api/power_control_device_outlet/"))
        self.assertEqual(pre_count, self.max_outlets)

        pdu = self.api_get_list("/api/power_control_device/")[0]
        self.api_client.delete(pdu['resource_uri'])

        post_count = len(self.api_get_list("/api/power_control_device_outlet/"))
        self.assertEqual(post_count, pre_count - self.max_outlets)

    def test_pdu_modifications(self):
        # After it's been created, it should be possible to modify most of a
        # PDU's attributes.
        test_fields = ["name", "address", "port", "username", "password", "options"]
        pdu = self.api_get_list("/api/power_control_device/")[0]

        new_values = dict([(f, str(pdu[f]) + "changed") for f in test_fields])
        new_values['address'] = '127.0.0.2'
        new_values['port'] = '4242'

        # Tastypie 0.9.11 doesn't like nested PUTs with full resources
        pdu['device_type'] = pdu['device_type']['resource_uri']
        pdu['outlets'] = [o['resource_uri'] for o in pdu['outlets']]

        for k, v in new_values.items():
            pdu[k] = v
        self.api_client.put(pdu['resource_uri'], data = pdu)

        pdu = self.api_get_list("/api/power_control_device/")[0]
        updated_fields = [f for f in test_fields if str(pdu[f]) == new_values[f]]

        self.assertEqual(test_fields, updated_fields)

    def test_hostname_lookup_for_pdu_address(self):
        # We store the address as an IPv4 address, but we should accept
        # a hostname.
        self._create_power_device(device_type = self.pdu_type['resource_uri'],
                                  address = 'localhost')

        pdu = self.api_get_list("/api/power_control_device/")[1]
        self.assertEqual(pdu['address'], '127.0.0.1')

    def test_bad_pdu_hostname(self):
        # A wonky PDU hostname should result in a ValidationError and
        # ultimately an AssertionError in the test harness.
        with self.assertRaisesRegexp(AssertionError, "Unable to resolve"):
            kwargs = {'device_type': self.pdu_type['resource_uri'],
                      'address': 'localtoast'}
            self._create_power_device(**kwargs)

    def test_dupe_sockaddr_raises_useful_error(self):
        # Make sure that entering a duplicate (address, port) combination
        # results in something informative coming back to the user.
        with self.assertRaises(AssertionError):
            kwargs = {'device_type': self.pdu_type['resource_uri'],
                      'address': '1.2.3.4'}
            self._create_power_device(**kwargs)
