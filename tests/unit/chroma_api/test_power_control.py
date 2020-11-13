import mock

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_api.test_misc import remove_host_resources_patch
from tests.unit.chroma_core.helpers import synthetic_host, log
from chroma_core.models.power_control import PowerControlDevice
from chroma_core.models.host import RemoveHostJob
from iml_common.lib.agent_rpc import agent_result_ok


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

        PowerControlRpc._call = mock.Mock(side_effect=rpc_local)

    def _create_resource(self, create_uri, **kwargs):
        response = self.api_client.post(create_uri, data=kwargs)
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
        default_username = "apc"
        default_password = "apc"
        power_type = self._create_power_type(
            agent="fence_apc",
            make="FAKE",
            model="FAKE",
            max_outlets=8,
            default_username=default_username,
            default_password=default_password,
            default_options="foo=x",
        )

        new_pdu = self._create_power_device(device_type=power_type["resource_uri"], address="1.2.3.4")

        db_pdu = PowerControlDevice.objects.get(id=new_pdu["id"])
        self.assertEqual(new_pdu["name"], new_pdu["address"])
        self.assertEqual(new_pdu["port"], power_type["default_port"])
        self.assertEqual(db_pdu.username, default_username)
        self.assertEqual(db_pdu.password, default_password)
        self.assertEqual(new_pdu["options"], power_type["default_options"])

    def test_creation_with_all_values_supplied(self):
        username = "super"
        password = "s3kr3t"
        power_type = self._create_power_type(
            agent="fence_apc",
            make="FAKE",
            model="FAKE",
            max_outlets=8,
            default_username="apc",
            default_password="apc",
            default_options="foo=x",
        )

        new_pdu = self._create_power_device(
            device_type=power_type["resource_uri"],
            name="foopdu",
            address="1.2.3.4",
            port=2300,
            username=username,
            password=password,
            options="foo=y",
        )

        db_pdu = PowerControlDevice.objects.get(id=new_pdu["id"])
        self.assertEqual(new_pdu["name"], "foopdu")
        self.assertEqual(new_pdu["port"], 2300)
        self.assertEqual(db_pdu.username, username)
        self.assertEqual(db_pdu.password, password)
        self.assertEqual(new_pdu["options"], "foo=y")


class PowerControlResourceTests(PowerControlResourceTestCase):
    def setUp(self):
        super(PowerControlResourceTests, self).setUp()

        self.max_outlets = 8

        self.pdu_type = self._create_power_type(
            agent="fence_apc", default_username="apc", default_password="apc", max_outlets=self.max_outlets
        )
        self.pdu = self._create_power_device(device_type=self.pdu_type["resource_uri"], address="1.2.3.4")

    def test_pdu_devices_prepopulate_outlets(self):
        outlets = self.api_get(self.pdu["resource_uri"])["outlets"]
        pdu_count = len(self.api_get_list("/api/power_control_device/"))
        self.assertEqual(len(outlets), self.max_outlets * pdu_count)

    def test_adding_more_than_max_outlets(self):
        with self.assertRaisesRegexp(AssertionError, ".*max.*outlets.*"):
            self._create_power_outlet(device=self.pdu["resource_uri"], identifier=self.max_outlets + 1)

        outlets = self.api_get(self.pdu["resource_uri"])["outlets"]
        self.assertEqual(len(outlets), self.max_outlets)

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify")
    def test_associating_outlets_with_hosts(self, notify):
        synthetic_host(address="foo")
        host = self.api_get_list("/api/host/")[0]

        outlet = self.api_get_list("/api/power_control_device_outlet/")[0]

        self.api_patch_attributes(outlet["resource_uri"], {"host": host["resource_uri"]})

        outlet = self.api_get(outlet["resource_uri"])
        self.assertEqual(outlet["host"], host["resource_uri"])

        self.assertTrue(notify.called)

    def test_deleting_devices_deletes_outlets(self):
        pre_count = len(self.api_get_list("/api/power_control_device_outlet/"))
        self.assertEqual(pre_count, self.max_outlets)

        pdu = self.api_get_list("/api/power_control_device/")[0]
        self.api_client.delete(pdu["resource_uri"])

        post_count = len(self.api_get_list("/api/power_control_device_outlet/"))
        self.assertEqual(post_count, pre_count - self.max_outlets)

    def test_pdu_modifications(self):
        # After it's been created, it should be possible to modify most of a
        # PDU's attributes.
        test_fields = ["name", "address", "port", "options"]
        pdu = self.api_get_list("/api/power_control_device/")[0]

        new_values = dict([(f, str(pdu[f]) + "changed") for f in test_fields])
        new_values["address"] = "127.0.0.2"
        new_values["port"] = "4242"

        # Tastypie 0.9.16 doesn't like nested PUTs with full resources
        pdu["device_type"] = pdu["device_type"]["resource_uri"]
        pdu["outlets"] = [o["resource_uri"] for o in pdu["outlets"]]

        for k, v in new_values.items():
            pdu[k] = v
        self.api_client.put(pdu["resource_uri"], data=pdu)

        pdu = self.api_get_list("/api/power_control_device/")[0]
        updated_fields = [f for f in test_fields if str(pdu[f]) == new_values[f]]

        self.assertEqual(test_fields, updated_fields)

    def test_hostname_lookup_for_pdu_address(self):
        # We store the address as an IPv4 address, but we should accept
        # a hostname.
        self._create_power_device(device_type=self.pdu_type["resource_uri"], address="localhost")

        pdu = self.api_get_list("/api/power_control_device/")[1]
        self.assertEqual(pdu["address"], "127.0.0.1")

    def test_bad_pdu_hostname(self):
        # A wonky PDU hostname should result in a ValidationError and
        # ultimately an AssertionError in the test harness.
        with self.assertRaisesRegexp(AssertionError, "Unable to resolve"):
            kwargs = {"device_type": self.pdu_type["resource_uri"], "address": "localtoast"}

            self._create_power_device(**kwargs)

    def test_dupe_sockaddr_raises_useful_error(self):
        # Make sure that entering a duplicate (address, port) combination
        # results in something informative coming back to the user.
        with self.assertRaises(AssertionError):
            kwargs = {"device_type": self.pdu_type["resource_uri"], "address": "1.2.3.4"}
            self._create_power_device(**kwargs)


class IpmiResourceTests(PowerControlResourceTestCase):
    def setUp(self):
        super(IpmiResourceTests, self).setUp()

        self.ipmi_type = self._create_power_type(
            agent="fence_ipmilan", default_username="foo", default_password="bar", max_outlets=0
        )

        self.ipmi = self._create_power_device(
            device_type=self.ipmi_type["resource_uri"], address="0.0.0.0", username="baz", password="qux"
        )

        self.host_obj = synthetic_host(address="foo")
        self.host = self.api_get_list("/api/host/")[0]

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify")
    def test_new_bmc_triggers_fence_reconfig(self, notify):
        bmc = self._create_power_outlet(
            host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="1.2.3.4"
        )

        self.assertEqual(bmc["identifier"], "1.2.3.4")
        self.assertEqual(bmc["host"], self.host["resource_uri"])
        self.assertEqual(bmc["device"], self.ipmi["resource_uri"])

        self.assertTrue(notify.called)

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify")
    def test_bmc_identifier_stored_as_ipaddr(self, notify):
        bmc = self._create_power_outlet(
            host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="localhost"
        )
        self.assertEqual(bmc["identifier"], "127.0.0.1")

        self.assertTrue(notify.called)

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify")
    def test_deleting_bmc(self, notify):
        bmc = self._create_power_outlet(
            host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="localhost"
        )
        self.assertEqual(1, notify.call_count)

        self.api_client.delete(bmc["resource_uri"])
        # Ensure that deleting the BMC triggers a fencing update too
        self.assertEqual(2, notify.call_count)

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify")
    def test_duplicate_bmc_address_rejected(self, notify):
        self._create_power_outlet(
            host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="localhost"
        )

        with self.assertRaises(AssertionError):
            self._create_power_outlet(
                host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="localhost"
            )

        self.assertEqual(1, notify.call_count)

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify")
    def test_adding_outlet_with_existing_bmc_is_rejected(self, notify):
        pdu_type = self._create_power_type(
            agent="fence_apc", default_username="foo", default_password="bar", max_outlets=1
        )

        pdu = self._create_power_device(
            device_type=pdu_type["resource_uri"], address="1.2.3.4", username="baz", password="qux"
        )

        self._create_power_outlet(
            host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="localhost"
        )

        outlet = pdu["outlets"][0]
        outlet["host"] = self.host["resource_uri"]
        r = self.api_client.put(outlet["resource_uri"], data=outlet)
        self.assertHttpBadRequest(r)

        self.assertEqual(1, notify.call_count)

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify")
    def test_adding_bmc_with_existing_outlet_is_rejected(self, notify):
        pdu_type = self._create_power_type(
            agent="fence_apc", default_username="foo", default_password="bar", max_outlets=1
        )

        pdu = self._create_power_device(
            device_type=pdu_type["resource_uri"], address="1.2.3.4", username="baz", password="qux"
        )

        outlet = pdu["outlets"][0]
        outlet["host"] = self.host["resource_uri"]
        r = self.api_client.put(outlet["resource_uri"], data=outlet)
        self.assertHttpOK(r)

        with self.assertRaises(AssertionError):
            self._create_power_outlet(
                host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="localhost"
            )

        self.assertEqual(1, notify.call_count)

    def test_unresolvable_bmc_identifier_invalid(self):
        with self.assertRaises(AssertionError):
            self._create_power_outlet(
                host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="not valid"
            )

    def test_confused_bmc_identifier_invalid(self):
        with self.assertRaises(AssertionError):
            self._create_power_outlet(host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="1")

    @mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify", new=mock.Mock())
    @mock.patch("chroma_core.services.http_agent.HttpAgentRpc.remove_host", new=mock.Mock(), create=True)
    @mock.patch("chroma_core.services.job_scheduler.agent_rpc.AgentRpc.remove", new=mock.Mock())
    @mock.patch("chroma_core.lib.job.Step.invoke_agent", new=mock.Mock(return_value=agent_result_ok))
    @mock.patch("chroma_core.lib.influx.influx_post", new=mock.Mock())
    @remove_host_resources_patch
    def test_removed_host_deletes_bmc(self):
        bmc = self._create_power_outlet(
            host=self.host["resource_uri"], device=self.ipmi["resource_uri"], identifier="localhost"
        )
        self.assertDictEqual(bmc, self.api_get_list("/api/power_control_device_outlet/")[0])

        job = RemoveHostJob(host=self.host_obj)
        for step_klass, args in job.get_steps():
            step_klass(job, args, None, None, None).run(args)

        # The BMC should have been removed when the host was removed
        with self.assertRaises(IndexError):
            self.api_get_list("/api/power_control_device_outlet/")[0]
