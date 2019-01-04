import logging
import time
import json

from collections import namedtuple
from testconfig import config
from tests.integration.core.api_testcase_with_test_reset import ApiTestCaseWithTestReset
from tests.integration.core.constants import LONG_TEST_TIMEOUT, INSTALL_TIMEOUT
from tests.utils.check_server_host import check_nodes_status

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)


class ChromaIntegrationTestCase(ApiTestCaseWithTestReset):
    """The TestCase class all chroma integration test cases should inherit form.

    This class ties together the common functionality needed in most
    integration test cases. For functionality used in a limited subset
    of tests, please see the *_testcase_mixin modules in this same directory.
    """

    def __init__(self, methodName="runTest"):
        super(ChromaIntegrationTestCase, self).__init__(methodName)
        self._standard_filesystem_layout = None

    def get_named_profile(self, profile_name):
        all_profiles = self.chroma_manager.get("/api/server_profile/").json["objects"]
        filtered_profile = [profile for profile in all_profiles if profile["name"] == profile_name]

        assert len(filtered_profile) == 1

        return filtered_profile[0]

    def get_current_host_profile(self, host):
        """Return the profile currently running on the host."""
        return self.chroma_manager.get("/api/server_profile/?name=%s" % host["server_profile"]["name"]).json["objects"][
            0
        ]

    def get_best_host_profile(self, address):
        """
        Return the most suitable profile for the host.

        This suitability is done using the profile validation rules.
        """
        host = next(h for h in config["lustre_servers"] if h["address"] == address)

        # If the host actually specified a profile in the configuration, then I think it's fair
        # to say that must be the best one.
        if host.get("profile"):
            return self.get_named_profile(host["profile"])

        all_profiles = self.chroma_manager.get("/api/server_profile/").json["objects"]

        # Get the one for this host.
        host_validations = self.get_valid_host_validations(host).profiles

        # Merge the two so we have single list.
        for profile in all_profiles:
            profile["validations"] = host_validations[profile["name"]]

        # Filter by managed.
        filtered_profile = [
            profile
            for profile in all_profiles
            if (
                profile["managed"] == config.get("managed", False)
                and profile["worker"] is False
                and profile["user_selectable"] is True
            )
        ]

        # Finally get one that pass all the tests, get the whole list and validate there is only one choice
        filtered_profile = [profile for profile in filtered_profile if self._validation_passed(profile["validations"])]

        assert len(filtered_profile) == 1

        return filtered_profile[0]

    def _validation_passed(self, validations):
        for validation in validations:
            if validation["pass"] is False:
                return False

        return True

    HostProfiles = namedtuple("HostProfiles", ["profiles", "valid"])

    def get_host_validations(self, host):
        """
        Returns the host validations for the host passed.

        :param host: Host to get profiles for.
        :return: HostProfiles named tuple.
        """

        all_validations = self.chroma_manager.get("/api/host_profile").json["objects"]

        # Return the one for this host.
        validation = next(
            validation["host_profiles"]
            for validation in all_validations
            if validation["host_profiles"]["address"] == host["address"]
        )

        # Old API's don't have profiles_valid, so return work out the answer.
        if "profiles_valid" not in validation:
            validation["profiles_valid"] = (
                self.chroma_manager.get("api/host/%s" % validation["host"]).json["properties"] != "{}"
            )

        return self.HostProfiles(validation["profiles"], validation["profiles_valid"])

    def get_valid_host_validations(self, host):
        """
        Returns the host validations for the host passed. The routine will wait for the validations to be valid
        before returning. If they do not become valid it will assert.

        :param host: Host to get profiles for.
        :return: HostProfiles named tuple.
        """
        self.wait_for_assert(lambda: self.assertTrue(self.get_host_validations(host).valid))

        return self.get_host_validations(host)

    def _validate_hosts(self, addresses, auth_type):
        """
        Verify server checks pass for provided addresses.

        A single validation of the addresses provided that raises an exception if any of the addresses do not
        pass validation.

        :param addresses: List of addresses to validate for agent install
        :param auth_type: Type of authentication to use.
        """

        response = self.chroma_manager.post(
            "/api/test_host/", body={"objects": [{"address": address, "auth_type": auth_type} for address in addresses]}
        )

        self.assertEqual(response.successful, True, response.text)

        for object in response.json["objects"]:
            self.wait_for_command(self.chroma_manager, object["command"]["id"])
            for job in object["command"]["jobs"]:
                response = self.chroma_manager.get(job)
                self.assertTrue(response.successful, response.text)
                host_info = response.json["step_results"].values()[0]
                address = host_info.pop("address")
                for result in host_info["status"]:
                    self.assertTrue(
                        result["value"],
                        "Expected %s to be true for %s, but instead found %s. JSON for host: %s"
                        % (result["name"], address, result["value"], response.json),
                    )

    def validate_hosts(self, addresses, auth_type="existing_keys_choice"):
        """
        Verify server checks pass for provided addresses.

        Sometimes the verify check will return failure before returning success. So we actually repeat the call
        if there are failures. This is not an unreasonable thing to do as a user will just sit and wait for the
        red boxes to turn to green boxes.

        After a timeout an assertion is raised if the hosts have not all validated.

        :param addresses: List of addresses to validate for agent install
        :param auth_type: Type of authentication to use.
        """

        self.wait_for_assert(lambda: self._validate_hosts(addresses, auth_type))

    def deploy_agents(self, addresses, auth_type="existing_keys_choice"):
        """Deploy the agent to the addresses provided"""
        response = self.chroma_manager.post(
            "/api/host/",
            body={
                "objects": [
                    {"address": address, "auth_type": auth_type, "server_profile": "/api/server_profile/default/"}
                    for address in addresses
                ]
            },
        )
        self.assertEqual(response.successful, True, response.text)

        command_ids = []
        for object in response.json["objects"]:
            host = object["command_and_host"]["host"]
            host_address = [host["address"]][0]
            self.assertTrue(host["id"])
            self.assertTrue(host_address)
            command_ids.append(object["command_and_host"]["command"]["id"])

            response = self.chroma_manager.get("/api/host/%s/" % host["id"])
            self.assertEqual(response.successful, True, response.text)
            host = response.json
            self.assertEqual(host["address"], host_address)

            # At this point the validations should be invalid the host is added but not deployed yet.
            self.assertFalse(self.get_host_validations(host).valid)

        # Wait for deployment to complete
        self.wait_for_commands(self.chroma_manager, command_ids)

    def set_host_profiles(self, hosts):
        # Set the profile for each new host
        response = self.chroma_manager.post(
            "/api/host_profile/",
            body={
                "objects": [
                    {"host": h["id"], "profile": self.get_best_host_profile(h["address"])["name"]} for h in hosts
                ]
            },
        )
        self.assertEqual(response.successful, True, response.text)
        # Wait for the server to be set up with the new server profile
        # Rather a long timeout because this may be installing packages, including Lustre and a new kernel
        command_ids = []
        for object in response.json["objects"]:
            for command in object["commands"]:
                command_ids.append(command["id"])

        def check_for_HYD_2849_4050():
            # Debugging added for HYD-2849, must not impact normal exception handling
            check_nodes_status(config)
            # HYD-4050: spin here so that somebody can inspect if we hit this bug
            for command_id in command_ids:
                command = self.get_json_by_uri("/api/command/%s/" % command_id)
                for job_uri in command["jobs"]:
                    job = self.get_json_by_uri(job_uri)
                    job_steps = [self.get_json_by_uri(s) for s in job["steps"]]
                    if job["errored"]:
                        for step in job_steps:
                            if step["state"] == "failed" and step["console"].find("is no initramfs") >= 0:
                                return True

            return False

        self._fetch_help(
            lambda: self.wait_for_commands(self.chroma_manager, command_ids, timeout=INSTALL_TIMEOUT),
            ["iml@whamcloud.com"],
            "Waiting for developer inspection.  DO NOT ABORT THIS TEST.",
            timeout=60 * 60 * 24 * 3,
        )

    def _add_hosts(self, addresses, auth_type):
        """Add a list of lustre server addresses to chroma and ensure lnet ends in the correct state."""
        self.validate_hosts(addresses, auth_type)
        self.deploy_agents(addresses, auth_type)
        self.set_host_profiles(self.get_hosts(addresses))

        # Verify the new hosts are now in the database and in the correct state
        new_hosts = self.get_hosts(addresses)
        self.assertEqual(len(new_hosts), len(addresses), new_hosts)

        # Setup pacemaker debugging
        self.execute_simultaneous_commands(
            [
                "grep -q ^PCMK_debug /etc/sysconfig/pacemaker || echo PCMK_debug=crmd,pengine,stonith-ng >> /etc/sysconfig/pacemaker",
                "systemctl try-restart pacemaker",
            ],
            [x["fqdn"] for x in new_hosts],
            "Set pacemaker debug for test",
            expected_return_code=None,
        )

        for host in new_hosts:
            # Deal with pre-3.0 versions.
            if host["state"] in ["lnet_up", "lnet_down", "lnet_unloaded"]:
                if self.get_current_host_profile(host)["name"] == "base_managed":
                    self.assertEqual(host["state"], "lnet_up", host)
                else:
                    self.assertIn(host["state"], ["lnet_up", "lnet_down", "lnet_unloaded"], host)
            else:
                self.assertEqual(host["state"], self.get_current_host_profile(host)["initial_state"], host)

        # Make sure the agent config is flushed to disk
        self.remote_operations.sync_disks([h["address"] for h in new_hosts])

        return new_hosts

    def add_hosts(self, addresses, auth_type="existing_keys_choice"):
        """
        Add a list of lustre server addresses to chroma and ensure lnet ends in the correct state.

        If the quick_setup is enabled then this will shortcut by adding any hosts in the list of addresses that do not
        already exists.

        :param addresses: list of host addresses to add
        :param auth_type: Type of authentication to add
        :return: Host configured in IML.
        """
        if self.quick_setup:
            existing_hosts = self.get_hosts()
            addresses_to_add = list(set(addresses) - set([host["address"] for host in existing_hosts]))
        else:
            addresses_to_add = addresses

        self._add_hosts(addresses_to_add, auth_type)

        return self.get_hosts(addresses)

    def get_hosts(self, addresses=None):
        """
        Get the hosts from the api for all or subset of hosts.

        Keyword arguments:
        addresses: If provided, limit results to addresses specified.
        """
        response = self.chroma_manager.get("/api/host/")
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json["objects"]
        if addresses is not None:
            hosts = [host for host in hosts if host["address"] in addresses]
        return hosts

    @property
    def standard_filesystem_layout(self):
        self.assertIsNotNone(self._standard_filesystem_layout)

        return self._standard_filesystem_layout

    def create_filesystem_standard(self, test_servers, name="testfs", hsm=False):
        """Create a standard, basic filesystem configuration.
        One MGT, one MDT, in an active/active pair
        Two OSTs in an active/active pair"""
        # Add hosts as managed hosts
        self.assertGreaterEqual(len(test_servers), 4)
        host_addresses = [s["address"] for s in test_servers[:4]]
        hosts = self.add_hosts(host_addresses)

        self.configure_power_control(host_addresses)

        self.assertGreaterEqual(
            4,
            len(hosts),
            "Must have added at least 4 hosts before calling standard_filesystem_layout. Found '%s'" % hosts,
        )

        # Count how many of the reported Luns are ready for our test
        # (i.e. they have both a primary and a failover node)
        ha_volumes = self.wait_for_shared_volumes(4, 4)

        # Set primary and failover mounts explicitly and check they are respected
        self.set_volume_mounts(ha_volumes[0], hosts[0]["id"], hosts[1]["id"])
        self.set_volume_mounts(ha_volumes[1], hosts[1]["id"], hosts[0]["id"])
        self.set_volume_mounts(ha_volumes[2], hosts[2]["id"], hosts[3]["id"])
        self.set_volume_mounts(ha_volumes[3], hosts[3]["id"], hosts[2]["id"])

        # Configure for hsm if needed
        mdt_params = {}
        if hsm:
            mdt_params["mdt.hsm_control"] = "enabled"

        # Create new filesystem
        filesystem_id = self.create_filesystem(
            hosts,
            {
                "name": name,
                "mgt": {"volume_id": ha_volumes[0]["id"]},
                "mdts": [{"volume_id": ha_volumes[1]["id"], "conf_params": mdt_params}],
                "osts": [
                    {"volume_id": ha_volumes[2]["id"], "conf_params": {}},
                    {"volume_id": ha_volumes[3]["id"], "conf_params": {}},
                ],
                "conf_params": {},
            },
        )

        filesystem = self.get_filesystem(filesystem_id)

        # osts come back as uri's by default we want the objects so convert.
        filesystem["osts"] = [self.get_json_by_uri(ost_uri) for ost_uri in filesystem["osts"]]

        self._standard_filesystem_layout = {
            "mgt": {
                "primary_host": self.get_json_by_uri(filesystem["mgt"]["primary_server"]),
                "failover_host": self.get_json_by_uri(filesystem["mgt"]["failover_servers"][0]),
                "volume": filesystem["mgt"]["volume"],
            },
            "mdt": {
                "primary_host": self.get_json_by_uri(filesystem["mdts"][0]["primary_server"]),
                "failover_host": self.get_json_by_uri(filesystem["mdts"][0]["failover_servers"][0]),
                "volume": filesystem["mdts"][0]["volume"],
            },
            "ost1": {
                "primary_host": self.get_json_by_uri(filesystem["osts"][0]["primary_server"]),
                "failover_host": self.get_json_by_uri(filesystem["osts"][0]["failover_servers"][0]),
                "volume": filesystem["osts"][0]["volume"],
            },
            "ost2": {
                "primary_host": self.get_json_by_uri(filesystem["osts"][1]["primary_server"]),
                "failover_host": self.get_json_by_uri(filesystem["osts"][1]["failover_servers"][0]),
                "volume": filesystem["osts"][1]["volume"],
            },
        }

        # Define where we expect targets for volumes to be started on based on how we set volume mounts.
        volumes_expected_hosts = {
            self.standard_filesystem_layout["mgt"]["volume"]["id"]: hosts[0],
            self.standard_filesystem_layout["mdt"]["volume"]["id"]: hosts[1],
            self.standard_filesystem_layout["ost1"]["volume"]["id"]: hosts[2],
            self.standard_filesystem_layout["ost2"]["volume"]["id"]: hosts[3],
        }

        # Verify targets are started on the correct hosts
        self.check_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts, True)

        return filesystem_id

    def create_filesystem(self, hosts, filesystem, verify_successful=True):
        """
        Specify a filesystem to be created by chroma.

        Example usage:
            filesystem_id = self.create_filesystem(hosts,
                                                   {'name': 'testfs',
                                                    'mgt': {'volume_id': mgt_volume['id']},
                                                    'mdts': [{'volume_id': mdt_volume['id'], 'conf_params': {}}],
                                                    'osts': [{'volume_id': v['id'], 'conf_params': {}} for v in [ost_volume_1, ost_volume_2]],
                                                    'conf_params': {}})
        """
        # Ensure the hosts for the filesystem have power control, in case the
        # test author forgot, to ensure we test with a supported configuration.
        self.verify_power_control_configured(hosts)

        response = self.chroma_manager.post("/api/filesystem/", body=filesystem)

        self.assertTrue(response.successful, response.text)
        filesystem_id = response.json["filesystem"]["id"]
        command_id = response.json["command"]["id"]

        self.wait_for_command(
            self.chroma_manager, command_id, verify_successful=verify_successful, timeout=LONG_TEST_TIMEOUT
        )

        # Verify mgs and fs targets in pacemaker config for hosts
        self.remote_operations.check_ha_config(hosts, filesystem["name"])

        return filesystem_id

    def stop_filesystem(self, filesystem_id):
        response = self.chroma_manager.put("/api/filesystem/%s/" % filesystem_id, body={"state": "stopped"})
        self.assertTrue(response.successful, response.text)
        self.wait_for_command(self.chroma_manager, response.json["command"]["id"])

    def start_filesystem(self, filesystem_id):
        response = self.chroma_manager.put("/api/filesystem/%s/" % filesystem_id, body={"state": "available"})
        self.assertTrue(response.successful, response.text)
        self.wait_for_command(self.chroma_manager, response.json["command"]["id"])

    def create_client_mount(self, host_uri, filesystem_uri, mountpoint):
        # Normally this is done as part of copytool creation, but we need
        # to give the test harness some way of doing it via API.
        response = self.chroma_manager.post(
            "/api/client_mount/", body=dict(host=host_uri, filesystem=filesystem_uri, mountpoint=mountpoint)
        )
        self.assertTrue(response.successful, response.text)
        return response.json["client_mount"]

    def get_shared_volumes(self, required_hosts):
        """
        Return a list of shared storage volumes (have a primary and secondary node)
        """
        volumes = self.get_usable_volumes()

        ha_volumes = []
        for v in volumes:
            print(v)
            has_primary = len([node for node in v["volume_nodes"] if node["primary"]]) == 1
            has_two = len([node for node in v["volume_nodes"] if node["use"]]) >= 2
            accessible_enough = len(v["volume_nodes"]) >= required_hosts
            if has_primary and has_two and accessible_enough:
                ha_volumes.append(v)

        logger.info("Found these HA volumes: '%s'" % json.dumps(ha_volumes, indent=4, sort_keys=True))

        return ha_volumes

    def wait_for_shared_volumes(self, expected_volumes, required_hosts):
        self.wait_until_true(lambda: len(self.get_shared_volumes(required_hosts)) >= expected_volumes)

        return self.get_shared_volumes(required_hosts)

    def get_usable_volumes(self):
        response = self.chroma_manager.get("/api/volume/", params={"category": "usable", "limit": 0})
        self.assertEqual(response.successful, True, response.text)
        volumes = response.json["objects"]
        return self.filter_for_permitted_volumes(volumes)

    def wait_usable_volumes(self, required_volume_count):
        def at_least_n_volumes(required_volumes):
            return len(self.get_usable_volumes()) >= required_volumes

        self.wait_until_true(lambda: at_least_n_volumes(required_volume_count))

        return self.get_usable_volumes()

    def filter_for_permitted_volumes(self, volumes):
        """
        Take a list of volumes and return the members of the list that are also in the config.
        This is an extra check so that if there is a bug in the chroma volume detection,
        we won't go wiping other volumes the person running the tests cares about.
        """
        permitted_volumes = []
        for volume in volumes:
            for volume_node in volume["volume_nodes"]:
                host = self.chroma_manager.get(volume_node["host"]).json
                host_config = self.get_host_config(host["nodename"])
                if host_config:
                    if volume_node["path"] in host_config["device_paths"]:
                        permitted_volumes.append(volume)
                        break
                    else:
                        logger.warning("%s not in %s" % (volume_node["path"], host_config["device_paths"]))
                else:
                    logger.warning("No host config for '%s'" % host["nodename"])
        return permitted_volumes

    def set_volume_mounts(self, volume, primary_host_id, secondary_host_id):
        primary_volume_node_id = None
        secondary_volume_node_id = None
        for node in volume["volume_nodes"]:
            if node["host_id"] == int(primary_host_id):
                primary_volume_node_id = node["id"]
            elif node["host_id"] == int(secondary_host_id):
                secondary_volume_node_id = node["id"]

        self.assertTrue(primary_volume_node_id, volume)
        self.assertTrue(secondary_volume_node_id, volume)

        response = self.chroma_manager.put(
            "/api/volume/%s/" % volume["id"],
            body={
                "id": volume["id"],
                "nodes": [
                    {"id": secondary_volume_node_id, "primary": False, "use": True},
                    {"id": primary_volume_node_id, "primary": True, "use": True},
                ],
            },
        )
        self.assertTrue(response.successful, response.text)

    def create_power_control_type(self, body):
        response = self.chroma_manager.post("/api/power_control_type/", body=body)
        self.assertTrue(response.successful, response.text)
        return response.json

    def create_power_control_device(self, body):
        response = self.chroma_manager.post("/api/power_control_device/", body=body)
        self.assertTrue(response.successful, response.text)
        return response.json

    def create_power_control_device_outlet(self, body):
        response = self.chroma_manager.post("/api/power_control_device_outlet/", body=body)
        self.assertTrue(response.successful, response.text)
        return response.json

    def configure_power_control(self, host_addresses):
        # Set up power control for fencing -- needed to ensure that
        # failover completes. Pacemaker won't fail over the resource
        # if it can't STONITH the primary.
        if not config.get("power_control_types", False):
            return

        logger.info("Configuring power control on %s" % host_addresses)

        # clear out existing power stuff
        self.api_clear_resource("power_control_type")
        # Ensure that this stuff gets cleaned up, no matter what
        self.addCleanup(self.api_clear_resource, "power_control_type")

        power_types = {}
        for power_type in config["power_control_types"]:
            obj = self.create_power_control_type(power_type)
            power_types[obj["name"]] = obj
            logger.debug("Created %s" % obj["resource_uri"])

        power_devices = {}
        for pdu in config["power_distribution_units"]:
            body = pdu.copy()
            try:
                body["device_type"] = power_types[pdu["type"]]["resource_uri"]
            except KeyError:
                logger.debug(pdu["type"])
                logger.debug(power_types)
            del body["type"]
            obj = self.create_power_control_device(body)
            power_devices["%s:%s" % (obj["address"], obj["port"])] = obj
            logger.debug("Created %s" % obj["resource_uri"])

        precreated_outlets = self.get_list("/api/power_control_device_outlet/", args={"limit": 0})

        for outlet in config["pdu_outlets"]:
            new = {"identifier": outlet["identifier"], "device": power_devices[outlet["pdu"]]["resource_uri"]}
            if "host" in outlet and outlet["host"] in host_addresses:
                hosts = self.get_list("/api/host/", args={"limit": 0})
                try:
                    host = [h for h in hosts if h["address"] == outlet["host"]][0]
                except IndexError:
                    raise RuntimeError("%s not found in /api/host/. Found '%s'" % (outlet["host"], hosts))
                new["host"] = host["resource_uri"]

            try:
                obj = next(
                    o
                    for o in precreated_outlets
                    if o["device"] == new["device"] and o["identifier"] == new["identifier"]
                )
                if "host" in new:
                    response = self.chroma_manager.patch(obj["resource_uri"], body={"host": new["host"]})
                    self.assertEqual(response.successful, True, response.text)
                    logger.debug("Updated %s" % obj)
            except StopIteration:
                obj = self.create_power_control_device_outlet(new)
                logger.debug("Created %s" % obj)

        # now show that it worked
        tries = 1
        while True:
            exit_loop = True
            for host_address in host_addresses:
                fencible_nodes = self.remote_operations.get_fence_nodes_list(host_address, ignore_failure=True)
                logger.debug("Fencible nodes on %s are: %s" % (host_address, fencible_nodes))
                if len(fencible_nodes) < 1:
                    exit_loop = False
            if exit_loop or tries > 10:
                break
            tries += 1
            time.sleep(1)

        self.assertTrue(exit_loop, "All nodes have fencing set up")

    def verify_power_control_configured(self, hosts):
        outlets = self.get_list("/api/power_control_device_outlet/")
        hosts_with_outlets = set(o["host"] for o in outlets if o["host"] is not None)
        expected_hosts = set(h["resource_uri"] for h in hosts)
        for host in expected_hosts:
            self.assertIn(
                host,
                hosts_with_outlets,
                "Attempted to create a filesystem on a host without power control. Hosts expected: (%s) Hosts found to have outlets: (%s)"
                % (expected_hosts, hosts_with_outlets),
            )

    LNetInfo = namedtuple("LNetInfo", ("nids", "network_interfaces", "lnet_configuration", "host"))

    def _get_lnet_info(self, host):
        """
        :return: Returns a named tuple of network and lnet configuration or None if lnet configuration is not provided
                 by the version of the manager
        """

        # Check that the version of the manager running supports lnet_configuration.
        if "lnet_configuration" not in self.chroma_manager_api:
            return None

        # We fetch the host again so that it's state is updated.
        hosts = self.get_list("/api/host/", args={"fqdn": host["fqdn"]})
        self.assertEqual(len(hosts), 1, "Expected a single host to be returned got %s" % len(hosts))
        host = hosts[0]

        lnet_configuration = self.get_list(
            "/api/lnet_configuration", args={"host__id": host["id"], "dehydrate__nids": True, "dehydrate__host": True}
        )
        self.assertEqual(
            len(lnet_configuration),
            1,
            "Expected a single lnet configuration to be returned got %s" % len(lnet_configuration),
        )
        lnet_configuration = lnet_configuration[0]

        network_interfaces = self.get_list("/api/network_interface", args={"host__id": host["id"]})

        nids = self.get_list("/api/nid/", args={"lnet_configuration__id": lnet_configuration["id"]})

        logger.debug("Fetched Lnet info for %s" % host["fqdn"])
        logger.debug("Nid info %s" % nids)
        logger.debug("NetworkInterfaces info %s" % network_interfaces)
        logger.debug("LNetConfiguration info %s" % lnet_configuration)

        return self.LNetInfo(nids, network_interfaces, lnet_configuration, host)

    def targets_in_state(self, state):
        response = self.chroma_manager.get("/api/target/")
        self.assertEqual(response.successful, True, response.text)

        targets = response.json["objects"]
        mounted_targets = [t for t in targets if t["state"] == state]

        return len(mounted_targets) == len(targets)

    def check_targets_for_volumes_started_on_expected_hosts(
        self, filesystem_id, volumes_to_expected_hosts, assert_true
    ):
        """
        Private function providing shared logic for public facing target active host checks.
        """
        response = self.chroma_manager.get("/api/target/", params={"filesystem_id": filesystem_id})
        self.assertTrue(response.successful, response.text)
        targets = response.json["objects"]

        response = self.chroma_manager.get("/api/host/", params={})
        self.assertTrue(response.successful, response.text)
        hosts = response.json["objects"]

        for target in targets:
            expected_host = volumes_to_expected_hosts[target["volume"]["id"]]
            active_host = target["active_host"]
            if active_host is not None:
                active_host = [h["fqdn"] for h in hosts if h["resource_uri"] == active_host][0]
            logger.debug(
                "%s: should be running on %s (actual: %s)" % (target["name"], expected_host["fqdn"], active_host)
            )

            # Check manager's view
            if assert_true:
                self.assertEqual(expected_host["resource_uri"], target["active_host"])
            else:
                if not expected_host["resource_uri"] == target["active_host"]:
                    return False

            # Check corosync's view
            is_running = self.remote_operations.get_resource_running(expected_host, target["ha_label"])
            logger.debug("Manager says it's OK, pacemaker says: %s" % is_running)
            if assert_true:
                self.assertEqual(is_running, True)
            elif not is_running:
                return False

        return True
