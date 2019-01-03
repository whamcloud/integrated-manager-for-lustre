import logging
import os
import platform
import re
import time

import requests
from testconfig import config

from iml_common.lib import util
from tests.integration.core.constants import LONG_TEST_TIMEOUT
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.remote_operations import RealRemoteOperations
from tests.integration.core.utility_testcase import UtilityTestCase
from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice
from tests.utils.http_requests import AuthorizedHttpRequests
from tests.utils.http_requests import HttpRequests

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)


class ApiTestCaseWithTestReset(UtilityTestCase):
    """
    Adds convenience for interacting with the chroma api.
    """

    # Used by tests so that we don't need to be root
    COPYTOOL_TESTING_FIFO_ROOT = "/tmp"

    # Most tests do not need simulated PDUs, so don't bother starting them.
    # Flip this setting on a per-class basis for groups of tests which do
    # actually need PDUs.
    TESTS_NEED_POWER_CONTROL = False

    # By default, work with all configured servers.
    TEST_SERVERS = config["lustre_servers"]

    # Storage for details of the rest api provided by the manager. Presumes that the api does not change during
    # execution of the whole test suite and so stores the result once in a class variable. A class variable
    # because instances of this class come and go but the api today is constant.
    _chroma_manager_api = None

    _chroma_manager = None
    _unauthorized_chroma_manager = None

    def __init__(self, methodName="runTest"):
        super(ApiTestCaseWithTestReset, self).__init__(methodName)
        self.remote_operations = None
        self.down_node_expected = False

    def setUp(self):
        super(ApiTestCaseWithTestReset, self).setUp()

        self.remote_operations = RealRemoteOperations(self)

        storage_servers = [s for s in self.TEST_SERVERS if "worker" not in s.get("profile", "")]
        if self.quick_setup is False:
            # Ensure that all servers are up and available
            for server in storage_servers:
                logger.info("Checking that %s is running and restarting if necessary..." % server["fqdn"])
                self.remote_operations.await_server_boot(server["fqdn"], restart=True)
                logger.info("%s is running" % server["fqdn"])
                self.remote_operations.inject_log_message(server["fqdn"], "==== " "starting test %s " "=====" % self)

            if config.get("reset", True):
                self.reset_cluster()
            elif config.get("soft_reset", True):
                # Reset the manager via the API
                self.wait_until_true(self.api_contactable)
                self.api_force_clear()
                self.remote_operations.clear_ha(storage_servers)
                [
                    self.remote_operations.unmount_lustre_targets(x)
                    for x in storage_servers
                    if not self.remote_operations.is_worker(x)
                ]
                self.remote_operations.clear_lnet_config(self.TEST_SERVERS)

            if config.get("managed"):
                # Ensure that config from previous runs doesn't linger into
                # this one.
                self.remote_operations.remove_config(self.TEST_SERVERS)

                # If there are no configuration options for a given server
                # (e.g. corosync_config), then this is a noop and no config file
                # is written.
                self.remote_operations.write_config(self.TEST_SERVERS)

                # cleanup linux devices
                self.cleanup_linux_devices(storage_servers)

                self.cleanup_zpools()
                self.create_zpools()

            # Enable agent debugging
            self.remote_operations.enable_agent_debug(self.TEST_SERVERS)

    def tearDown(self):
        # TODO: move all of the (rest of the) "post-test cleanup" that is
        # done in setUp to here
        if config.get("managed"):
            self.remote_operations.unmount_clients()
            # stop any running filesystems
            for filesystem in [f for f in self.get_list("/api/filesystem/") if f["state"] == "available"]:
                logger.debug("stopping filesystem %s" % filesystem)
                self.stop_filesystem(filesystem["id"])
        else:
            if self.remote_operations:
                # Check that all servers are up and available after the test
                down_nodes = []
                for server in self.TEST_SERVERS:
                    if not self.remote_operations.host_contactable(server["address"]):
                        down_nodes.append(server["address"])
                    else:
                        self.remote_operations.inject_log_message(server["fqdn"], "==== stopping test %s =====" % self)

                if len(down_nodes) and (self.down_node_expected is False):
                    logger.warning("After test, some servers were no longer running: %s" % ", ".join(down_nodes))
                    raise RuntimeError("AWOL servers after test: %s" % ", ".join(down_nodes))

    @property
    def config_servers(self):
        return [s for s in config["lustre_servers"] if "worker" not in s.get("profile", "")]

    @property
    def config_workers(self):
        return [w for w in config["lustre_servers"] if "worker" in w.get("profile", "")]

    @property
    def chroma_manager(self):
        if self._chroma_manager is None:
            user = config["chroma_managers"][0]["users"][0]
            self._chroma_manager = AuthorizedHttpRequests(
                user["username"], user["password"], server_http_url=config["chroma_managers"][0]["server_http_url"]
            )
        return self._chroma_manager

    @property
    def unauthorized_chroma_manager(self):
        if self._unauthorized_chroma_manager is None:
            self._unauthorized_chroma_manager = HttpRequests(
                server_http_url=config["chroma_managers"][0]["server_http_url"]
            )
        return self._unauthorized_chroma_manager

    def restart_chroma_manager(self, fqdn):
        self.remote_operations.restart_chroma_manager(fqdn)

    def api_contactable(self):
        try:
            self.chroma_manager.get("/api/system_status/")
            return True
        except requests.ConnectionError:
            return False

    def _print_command(self, command, disposition, msg):
        print("COMMAND %s: %s" % (command["id"], disposition))
        print("-----------------------------------------------------------")
        print(command)
        if msg:
            print("Run to %s" % msg)
        print("")

        for job_uri in command["jobs"]:
            job = self.get_json_by_uri(job_uri)
            job_steps = [self.get_json_by_uri(s) for s in job["steps"]]
            if disposition == "FAILED":
                if job["errored"]:
                    print("Job %s Errored (%s):" % (job["id"], job["description"]))
                    print(job)
                    print("")
                    for step in job_steps:
                        if step["state"] == "failed":
                            print("Step %s failed:" % step["id"])
                            for k, v in step.iteritems():
                                print("%s: %s" % (k, v))
                            print("")
            elif disposition == "TIMED OUT":
                if job["state"] != "complete":
                    print("Job %s incomplete:" % job["id"])
                    print(job)
                    print("")
                    for step in job_steps:
                        if step["state"] == "incomplete":
                            print("Step %s incomplete:" % step["id"])
                            print(step)
                            print("")
            else:
                print(job)
                for step in job_steps:
                    print(step)

    def wait_for_command(
        self,
        chroma_manager,
        command_id,
        timeout=TEST_TIMEOUT,
        verify_successful=True,
        test_for_eventual_completion=True,
        msg=None,
    ):
        logger.debug("wait_for_command: %s" % self.get_json_by_uri("/api/command/%s/" % command_id))
        # TODO: More elegant timeout?
        running_time = 0
        command_complete = False
        while running_time < timeout and not command_complete:
            command = self.get_json_by_uri("/api/command/%s/" % command_id)
            command_complete = command["complete"]
            if not command_complete:
                time.sleep(1)
                running_time += 1

        if running_time >= timeout:
            self._print_command(command, "TIMED OUT", msg)

            # Now wait again to see if the command eventually succeeds. The test will still fail but we get some idea
            # if we just aren't waiting long enough of if there is an issue.
            if test_for_eventual_completion:
                retry_time = time.time()
                # If it fails the second time this will throw an exception and never return.
                self._print_command(
                    self.wait_for_command(
                        chroma_manager,
                        command_id,
                        timeout=timeout,
                        verify_successful=verify_successful,
                        test_for_eventual_completion=False,
                    ),
                    "COMPLETED %s SECONDS AFTER TIMEOUT" % int(time.time() - retry_time),
                    None,
                )
        else:
            logger.debug("command for %s complete: %s" % (msg, command))

        self.assertTrue(command_complete, "%s: --> %s" % (msg, command))
        if verify_successful and (command["errored"] or command["cancelled"]):
            self._print_command(command, "FAILED", msg)

            self.assertFalse(command["errored"] or command["cancelled"], command)

        return command

    def wait_for_commands(self, chroma_manager, command_ids, timeout=TEST_TIMEOUT, verify_successful=True):
        assert type(chroma_manager) is AuthorizedHttpRequests, (
            "chroma_manager is not an AuthorizedHttpRequests: %s" % chroma_manager
        )
        assert type(command_ids) is list, "command_ids is not an int: %s" % type(command_ids)
        assert type(timeout) is int, "timeout is not an int: %s" % type(timeout)
        assert type(verify_successful) is bool, "verify_successful is not a bool: %s" % type(verify_successful)

        for command_id in command_ids:
            self.wait_for_command(chroma_manager, command_id, timeout, verify_successful)

    def wait_last_command_complete(self, timeout=TEST_TIMEOUT, verify_successful=True):
        """
        This actually waits for all commands to be complete and then verifies that the last command completed successfully
        :param timeout: Time to wait for commands to complete
        :param verify_successful: True if we should verify the last command completed OK.
        :return: No return value
        """
        assert type(timeout) is int, "timeout is not an int: %s" % type(timeout)
        assert type(verify_successful) is bool, "verify_successful is not a bool: %s" % type(verify_successful)

        self.wait_for_assert(
            lambda: self.assertEqual(
                0, len(self.get_json_by_uri("/api/command/", args={"complete": False})["objects"])
            ),
            timeout,
        )

        if verify_successful:
            response = self.get_json_by_uri("/api/command/", args={"limit": 0})
            last_command = max(response["objects"], key=lambda command: int(command["id"]))
            self.wait_for_command(self.chroma_manager, last_command["id"], timeout, True)

    def wait_alerts(self, expected_alerts, **filters):
        "Wait and assert correct number of matching alerts."
        expected_alerts.sort()

        for _ in util.wait(TEST_TIMEOUT):
            alerts = [alert["alert_type"] for alert in self.get_list("/api/alert/", filters)]
            alerts.sort()
            if alerts == expected_alerts:
                return alerts

        raise AssertionError(alerts)

    def get_list(self, url, args=None):
        args = args if args else {}
        assert type(args) is dict, "args is not a dictionary: %s" % type(args)

        response = self.chroma_manager.get(url, params=args)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json["objects"]

    def get_by_uri(self, uri, args=None, verify_successful=True):
        args = args if args else {}
        assert type(args) is dict, "args is not a dictionary: %s" % type(args)
        assert type(verify_successful) is bool, "verify_successful is not a bool: %s" % type(verify_successful)

        response = self.chroma_manager.get(uri, params=args)

        if verify_successful:
            self.assertEqual(response.status_code, 200, response.content)

        return response

    def get_json_by_uri(self, uri, args=None, verify_successful=True):
        args = args if args else {}
        assert type(args) is dict, "args is not a dictionary: %s" % type(args)
        assert type(verify_successful) is bool, "verify_successful is not a bool: %s" % type(verify_successful)

        return self.get_by_uri(uri, args, verify_successful).json

    def wait_for_action(self, victim, timeout=TEST_TIMEOUT, **filters):
        """
        Check victim's available_actions until the desired action is available
        or the timeout is reached, filtering on action keys: class_name, state.
        """
        for _ in util.wait(timeout):
            actions = self.get_json_by_uri(victim["resource_uri"])["available_actions"]
            for action in actions:
                if all(action.get(key) == filters[key] for key in filters):
                    return action
        actions = [dict((key, action.get(key)) for key in filters) for action in actions]
        raise AssertionError("{0} not found in {1}".format(filters, actions))

    def run_command(self, jobs, message=None, verify_successful=True):
        message = message if message else "Test command"
        assert type(message) in [str, unicode], "message is not a str/unicode: %s" % type(message)
        assert type(verify_successful) is bool, "verify_successful is not a bool: %s" % type(verify_successful)

        logger.debug("Running %s (%s)" % (jobs, message))
        response = self.chroma_manager.post("/api/command/", body=dict(jobs=jobs, message=message))

        if verify_successful:
            self.assertTrue(response.successful, response.text)
            self.wait_for_command(self.chroma_manager, response.json["id"])
        return response

    def post_by_uri(self, uri, object, verify_successful=True):
        logger.debug("post_by_uri(%s, ...)" % uri)
        response = self.chroma_manager.post(uri, body=object)

        if response.status_code == 204:
            logger.warning("post_by_uri(%s, ...) - no-op" % uri)
            command = None
        else:
            self.assertEquals(response.status_code, 202, response.content)
            command = self.wait_for_command(
                self.chroma_manager, response.json["command"]["id"], verify_successful=verify_successful
            )

        return command

    VERIFY_SUCCESS_NO = 0
    VERIFY_SUCCESS_INSTANT = 1
    VERIFY_SUCCESS_WAIT = 2

    def set_value(self, uri, value_name, value, verify_successful=VERIFY_SUCCESS_INSTANT, msg=None):
        logger.debug("set_%s %s %s%s" % (value_name, uri, value, ": %s" % msg if msg else ""))
        object = self.get_json_by_uri(uri)
        # We do this because some objects will presume a put with 'state' is a state change.
        # Do it before the object value setting so that if state is being set we don't break it.
        object.pop("state", None)
        object[value_name] = value

        response = self.chroma_manager.put(uri, body=object)
        if response.status_code == 204:
            logger.warning("set_%s %s %s - no-op" % (value_name, uri, value))
            command = None
        else:
            self.assertEquals(response.status_code, 202, response.content)

            json = response.json

            if "cancelled" in json and "complete" in json and "errored" in json:
                command_id = json["id"]
            # If the state is not a change command will be none and so we have nothing to wait for.
            elif response.json["command"] is None:
                command_id = None
            else:
                command_id = json["command"]["id"]

            if command_id:
                command = self.wait_for_command(
                    self.chroma_manager,
                    command_id,
                    verify_successful=(verify_successful != self.VERIFY_SUCCESS_NO),
                    msg=msg,
                    timeout=LONG_TEST_TIMEOUT,
                )
            else:
                command = None

        if verify_successful == self.VERIFY_SUCCESS_INSTANT:
            self.assertValue(uri, value_name, value)
        elif verify_successful == self.VERIFY_SUCCESS_WAIT:
            self.wait_for_assert(lambda: self.assertValue(uri, value_name, value))

        return command

    def set_state(self, uri, state, verify_successful=True, msg=None):
        return self.set_value(
            uri, "state", state, self.VERIFY_SUCCESS_INSTANT if verify_successful else self.VERIFY_SUCCESS_NO, msg
        )

    def set_state_dry_run(self, uri, state):
        stateful_object = self.get_json_by_uri(uri)

        stateful_object["state"] = state
        stateful_object["dry_run"] = True

        response = self.chroma_manager.put(uri, body=stateful_object)

        self.assertEquals(response.status_code, 200, response.content)

        return response.json

    def delete_by_uri(self, uri, verify_successful=True):
        response = self.chroma_manager.delete(uri)

        if verify_successful:
            self.assertEqual(response.status_code, 204)

        return response

    def assertNoAlerts(self, uri, of_severity=None, of_type=None):
        """Fail if alert_item (as tastypie uri) is found in any active alerts"""

        # The intent of this method was to check for no alerts, but it was
        # really just checking no active alerts that have not been dismissed.
        # callers of this code, like test_alerting.py expected no alerts of
        # this type.  Now you can't have alerts in that state.  Users dismiss
        # alerts.  The code that created dismissed alerts, now creates alerts
        # in the warning state.
        # TODO: fix each test that calls this method to be sure the proper
        # state is being tested.

        data = {"active": True}
        if of_type is not None:
            data["alert_type"] = of_type
        if of_severity is not None:  # Severity should be 'ERROR', 'WARNING', 'INFO'
            data["severity"] = of_severity
        alerts = self.get_list("/api/alert/", data)
        self.assertNotIn(uri, [a["alert_item"] for a in alerts])

    def assertHasAlert(self, uri, of_severity=None, of_type=None):
        data = {"active": True}
        if of_severity is not None:  # Severity should be 'ERROR', 'WARNING', 'INFO'
            data["severity"] = of_severity
        if of_type is not None:
            data["alert_type"] = of_type
        alerts = self.get_list("/api/alert/", data)
        self.assertIn(uri, [a["alert_item"] for a in alerts], [a["alert_item"] for a in alerts])

    def get_alert(self, uri, regex=None, alert_type=None, active=True):
        """Given that there is an active alert for object `uri` whose
           message matches `regex`, return it.  Raise an AssertionError
           if no such alert exists"""

        all_alerts = self.get_list("/api/alert/", {"active": active, "limit": 0})
        alerts = [a for a in all_alerts if a["alert_item"] == uri]
        if not alerts:
            raise AssertionError("No alerts for object %s (alerts are %s)" % (uri, all_alerts))

        if regex is not None:
            alerts = [a for a in alerts if re.match(regex, a["message"])]
            if not alerts:
                raise AssertionError("No alerts for object %s matching %s (alerts are %s)" % (uri, regex, all_alerts))

        if alert_type is not None:
            alerts = [a for a in alerts if a["alert_type"] == alert_type]
            if not alerts:
                raise AssertionError("No alerts of type %s found (alerts are %s)" % (alert_type, all_alerts))

        if len(alerts) > 1:
            raise AssertionError("Multiple alerts match: %s" % alerts)

        return alerts[0]

    def assertValue(self, uri, value_name, value):
        logger.debug("assertValue %s %s %s" % (value_name, uri, value))
        obj = self.get_json_by_uri(uri)
        self.assertEqual(str(obj[value_name]), str(value))  # Convert to strings so we don't get type issues.

    def assertState(self, uri, state):
        self.assertValue(uri, "state", state)

    def get_filesystem(self, filesystem_id):
        return self.get_json_by_uri("/api/filesystem/%s/" % filesystem_id)

    def get_filesystem_by_name(self, name):
        filesystems = self.get_list("/api/filesystem/")
        try:
            return [f for f in filesystems if f["name"] == name][0]
        except IndexError:
            raise KeyError("No filesystem named %s" % name)

    @property
    def chroma_manager_api(self):
        """
        Provides the details of the rest api provided by the manager. Presumes that the api does not change during
        execution of the whole test suite and so stores the result once in a class variable. A class variable
        because instances of this class come and go but the api today is constant.

        The call to get_json_by_uri creates quite a lot of useful debug, but it is quite a lot of another advantage of
        only fetching the data once is the we only see the debug once.

        :return: hash of the api
        """
        if ApiTestCaseWithTestReset._chroma_manager_api is None:
            ApiTestCaseWithTestReset._chroma_manager_api = self.get_json_by_uri("/api/")

        return ApiTestCaseWithTestReset._chroma_manager_api

    def reset_cluster(self):
        """
        Will fully wipe a test cluster:
          - dropping and recreating the manager database
          - unmounting any lustre filesystems from the clients
          - unconfiguring any chroma targets in pacemaker
        """
        self.reset_chroma_manager_db()
        self.remote_operations.stop_agents(s["address"] for s in config["lustre_servers"])
        if config.get("managed"):
            self.remote_operations.clear_ha(self.TEST_SERVERS)
            [
                self.remote_operations.unmount_lustre_targets(x)
                for x in self.TEST_SERVERS
                if not self.remote_operations.is_worker(x)
            ]
            self.remote_operations.clear_lnet_config(self.TEST_SERVERS)

    def reset_chroma_manager_db(self):
        for chroma_manager in config["chroma_managers"]:
            superuser = [u for u in chroma_manager["users"] if u["super"]][0]

            # Stop all manager services
            result = self.remote_command(chroma_manager["address"], "chroma-config stop", expected_return_code=None)
            if not result.exit_status == 0:
                logger.warn(
                    "chroma-config stop failed: rc:%s out:'%s' err:'%s'"
                    % (result.exit_status, result.stdout, result.stderr)
                )

            # Completely nuke the database to start from a clean state.
            self.remote_command(chroma_manager["address"], "service postgresql stop && rm -fr /var/lib/pgsql/data/*")

            # Run chroma-config setup to recreate the database and start the manager.
            result = self.remote_command(
                chroma_manager["address"],
                "chroma-config setup %s %s %s %s &> config_setup.log"
                % (
                    superuser["username"],
                    superuser["password"],
                    chroma_manager.get("ntp_server", "localhost"),
                    "--no-dbspace-check",
                ),
                expected_return_code=None,
            )
            chroma_config_exit_status = result.exit_status
            if not chroma_config_exit_status == 0:
                result = self.remote_command(chroma_manager["address"], "cat config_setup.log")
                self.assertEqual(0, chroma_config_exit_status, "chroma-config setup failed: '%s'" % result.stdout)

            # Register the default bundles and profile again
            result = self.remote_command(
                chroma_manager["address"],
                "for bundle_meta in /var/lib/chroma/repo/*/%s/meta; do chroma-config bundle register $(dirname $bundle_meta); done &> config_bundle.log"
                % platform.dist()[1][0:1],
                expected_return_code=None,
            )
            chroma_config_exit_status = result.exit_status
            if not chroma_config_exit_status == 0:
                result = self.remote_command(chroma_manager["address"], "cat config_bundle.log")
                self.assertEqual(
                    0, chroma_config_exit_status, "chroma-config bundle register failed: '%s'" % result.stdout
                )

            result = self.remote_command(
                chroma_manager["address"], "ls /usr/share/chroma-manager/", expected_return_code=None
            )
            share_dir_contents = result.stdout
            self.assertEqual(
                0,
                result.exit_status,
                "Could not find /usr/share/chroma-manager on the Manager node!\n'%s' '%s'"
                % (share_dir_contents, result.stderr),
            )

            logger.debug("/usr/share/chroma-manager contents: %s" % share_dir_contents)

            # get a list of profiles and re-register them
            profiles = " ".join([line for line in share_dir_contents.split("\n") if line.endswith(".profile")])
            logger.debug("Found these profiles: %s" % profiles)
            result = self.remote_command(
                chroma_manager["address"],
                "for profile_pat in %s; do chroma-config profile register /usr/share/chroma-manager/$profile_pat; done &> config_profile.log"
                % profiles,
                expected_return_code=None,
            )
            chroma_config_exit_status = result.exit_status
            if not chroma_config_exit_status == 0:
                result = self.remote_command(chroma_manager["address"], "cat config_profile.log")
                self.assertEqual(
                    0, chroma_config_exit_status, "chroma-config profile register failed: '%s'" % result.stdout
                )

    def graceful_teardown(self, chroma_manager):
        """
        Removes all filesystems, MGSs, and hosts from chroma via the api.  This is
        not guaranteed to work, and should be done at the end of tests in order to
        verify that the manager instance was in a nice state, rather than
        in setUp/tearDown hooks to ensure a clean system.
        """
        response = chroma_manager.get("/api/filesystem/", params={"limit": 0})
        self.assertEqual(response.status_code, 200)
        filesystems = response.json["objects"]

        self.remote_operations.unmount_clients()

        if len(filesystems) > 0:
            # Remove filesystems
            remove_filesystem_command_ids = []
            for filesystem in filesystems:
                response = chroma_manager.delete(filesystem["resource_uri"])
                self.assertTrue(response.successful, response.text)
                command_id = response.json["command"]["id"]
                self.assertTrue(command_id)
                remove_filesystem_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_filesystem_command_ids, timeout=LONG_TEST_TIMEOUT)

        # Remove MGT
        response = chroma_manager.get("/api/target/", params={"kind": "MGT", "limit": 0})
        self.assertTrue(response.successful, response.text)
        mgts = response.json["objects"]

        if len(mgts) > 0:
            remove_mgt_command_ids = []
            for mgt in mgts:
                response = chroma_manager.delete(mgt["resource_uri"])
                command_id = response.json["command"]["id"]
                self.assertTrue(command_id)
                remove_mgt_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_mgt_command_ids)

        # Remove hosts
        response = chroma_manager.get("/api/host/", params={"limit": 0})
        self.assertTrue(response.successful, response.text)
        hosts = response.json["objects"]

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                response = chroma_manager.delete(host["resource_uri"])
                self.assertTrue(response.successful, response.text)
                command_id = response.json["command"]["id"]
                self.assertTrue(command_id)
                remove_host_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_host_command_ids, timeout=LONG_TEST_TIMEOUT)

        self.assertDatabaseClear()

    def api_clear_resource(self, resource):
        response = self.chroma_manager.get("/api/%s" % resource, params={"limit": 0})
        self.assertTrue(response.successful, response.text)
        objects = response.json["objects"]

        for obj in objects:
            response = self.chroma_manager.delete(obj["resource_uri"])
            self.assertTrue(response.successful, response.text)

    def api_force_clear(self):
        """
        Clears the Chroma instance via the API (by issuing ForceRemoveHost
        commands) -- note that this will *not* unconfigure storage servers or
        remove corosync resources: do that separately.
        """

        response = self.chroma_manager.get("/api/host/", params={"limit": 0})
        self.assertTrue(response.successful, response.text)
        hosts = response.json["objects"]

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                command = self.chroma_manager.post(
                    "/api/command/",
                    body={
                        "jobs": [{"class_name": "ForceRemoveHostJob", "args": {"host_id": host["id"]}}],
                        "message": "Test force remove hosts",
                    },
                ).json
                remove_host_command_ids.append(command["id"])

            self.wait_for_commands(self.chroma_manager, remove_host_command_ids)

        self.api_clear_resource("power_control_type")

    def assertDatabaseClear(self, chroma_manager=None):
        """
        Checks that the manager API is now clear of filesystems, targets,
        hosts and volumes.
        """

        if chroma_manager is None:
            chroma_manager = self.chroma_manager

        # Verify there are zero filesystems
        response = chroma_manager.get("/api/filesystem/", params={"limit": 0})
        self.assertTrue(response.successful, response.text)
        filesystems = response.json["objects"]
        self.assertEqual(0, len(filesystems))

        # Verify there are zero mgts
        response = chroma_manager.get("/api/target/", params={"kind": "MGT"})
        self.assertTrue(response.successful, response.text)
        mgts = response.json["objects"]
        self.assertEqual(0, len(mgts))

        # Verify there are now zero hosts in the database.
        response = chroma_manager.get("/api/host/")
        self.assertTrue(response.successful, response.text)
        hosts = response.json["objects"]
        self.assertEqual(0, len(hosts))

        # Verify there are now zero volumes in the database.
        response = chroma_manager.get("/api/volume/", params={"limit": 0})
        self.assertTrue(response.successful, response.text)
        volumes = response.json["objects"]
        self.assertEqual(0, len(volumes))

    def reset_accounts(self, chroma_manager):
        """Remove any user accounts which are not in the config (such as
        those left hanging by tests)"""

        configured_usernames = [u["username"] for u in config["chroma_managers"][0]["users"]]

        response = chroma_manager.get("/api/user/", data={"limit": 0})
        self.assertEqual(response.status_code, 200)
        for user in response.json["objects"]:
            if not user["username"] in configured_usernames:
                chroma_manager.delete(user["resource_uri"])

    @classmethod
    def linux_devices_exist(cls):
        return any(lustre_device["backend_filesystem"] == "ldiskfs" for lustre_device in config["lustre_devices"])

    @classmethod
    def zfs_devices_exist(cls):
        return any(lustre_device["backend_filesystem"] == "zfs" for lustre_device in config["lustre_devices"])

    def create_zpools(self):
        xs = self.config_servers
        server0 = xs[0]
        fqdns = [x["fqdn"] for x in xs]

        self.execute_simultaneous_commands(
            ["udevadm info --path=/module/zfs"], fqdns, "checking for zfs presence", expected_return_code=None
        )

        self.execute_simultaneous_commands(
            [
                "echo 100 > /sys/module/zfs/parameters/zfs_multihost_history",
                "echo 20 > /sys/module/zfs/parameters/zfs_multihost_fail_intervals",
            ],
            fqdns,
            "set multihost params for test",
            expected_return_code=None,
        )

        partprobe_devices = []
        for lustre_device in config["lustre_devices"]:
            if lustre_device["backend_filesystem"] == "zfs":
                zfs_device = TestBlockDevice("zfs", server0["orig_device_paths"][lustre_device["path_index"]])

                self.execute_commands(
                    zfs_device.create_device_commands, server0["fqdn"], "create zfs device %s" % zfs_device
                )

                partprobe_devices.append(server0["orig_device_paths"][lustre_device["path_index"]])

        if partprobe_devices:
            # only partprobe the devices we are cleaning, as we can get
            # EBUSY for the root disk for example
            self.execute_simultaneous_commands(
                ["partprobe %s" % " ".join(partprobe_devices), "udevadm settle"], fqdns, "sync partitions"
            )

    def cleanup_zpools(self):
        if self.zfs_devices_exist() is False:
            return

        xs = config["lustre_servers"][:4]
        fqdns = [x["fqdn"] for x in xs]

        # Attempt to unmount all lustre targets otherwise
        # we won't be able to export parent pool
        [self.remote_operations.unmount_lustre_targets(x) for x in xs]

        # If ZFS if not installed on the test servers, then presume no ZFS to clear from any.
        # Might need to improve on this moving forwards.
        self.execute_simultaneous_commands(
            ["udevadm info --path=/module/zfs"], fqdns, "checking for zfs presence", expected_return_code=None
        )

        server0 = xs[0]

        zfs_device_paths = [
            server0["orig_device_paths"][x["path_index"]]
            for x in config["lustre_devices"]
            if x["backend_filesystem"] == "zfs"
        ]

        [
            self.execute_simultaneous_commands(
                TestBlockDevice("zfs", x).clear_device_commands([x]),
                fqdns,
                "destroy zpool %s" % x,
                expected_return_code=None,
            )
            for x in zfs_device_paths
        ]

        def wipe(x):
            return "wipefs -a {0}".format(x)

        self.execute_commands([wipe(x) for x in zfs_device_paths], server0["fqdn"], "wiping disks")

        # only partprobe the devices we are cleaning, as we can get
        # EBUSY for the root disk for example
        self.execute_simultaneous_commands(
            ["partprobe %s" % " ".join(zfs_device_paths), "udevadm settle"], fqdns, "sync partitions"
        )

    def cleanup_linux_devices(self, test_servers):
        if self.linux_devices_exist() is False:
            return

        first_test_server = test_servers[0]

        def get_device_path(idx):
            return first_test_server["device_paths"][idx]

        def cleanup_str(x):
            return "wipefs -a {}".format(x)

        device_paths = [
            get_device_path(x["path_index"]) for x in config["lustre_devices"] if x["backend_filesystem"] == "ldiskfs"
        ]

        desc = "clear block devices {}".format(", ".join(device_paths))
        wipe_commands = map(cleanup_str, device_paths)
        self.execute_commands(wipe_commands, first_test_server["fqdn"], desc)

        # only partprobe the devices we are cleaning, as we can get
        # EBUSY for the root disk for example
        self.execute_simultaneous_commands(
            ["partprobe %s" % " ".join(device_paths), "udevadm settle"],
            [server["fqdn"] for server in test_servers],
            "sync partitions",
        )

    @property
    def quick_setup(self):
        """
        Defining IML_QUICK_TEST_SETUP will mean that test setup is shortened to enable hands on development and debug
        of to be quicker.  It is not intended to be safe to use for real tests and is not really a part way towards test
        optimization.  It is to reduce the cycle time of development where a 10 second test can take 20 minutes
        for each run.

        Use with caution, only use when running 1 test - not a series of tests etc.

        :return:
        """
        return "IML_QUICK_TEST_SETUP" in os.environ
