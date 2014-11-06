import datetime
import logging
import re
import os
import requests
import shutil
import sys
import time

from testconfig import config
from tests.utils.http_requests import AuthorizedHttpRequests
from tests.utils import wait

from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.utility_testcase import UtilityTestCase
from tests.integration.core.remote_operations import SimulatorRemoteOperations, RealRemoteOperations


logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


# Used by tests so that we don't need to be root
COPYTOOL_TESTING_FIFO_ROOT = "/tmp"


class ApiTestCase(UtilityTestCase):
    """
    Adds convenience for interacting with the chroma api.
    """
    # These are sufficient for tests existing at time of writing.
    # Tests may ask for different values by defining these at class scope.
    SIMULATOR_NID_COUNT = 1
    SIMULATOR_CLUSTER_SIZE = 2

    # Most tests do not need simulated PDUs, so don't bother starting them.
    # Flip this setting on a per-class basis for groups of tests which do
    # actually need PDUs.
    TESTS_NEED_POWER_CONTROL = False

    # By default, work with all configured servers. Tests which will
    # only ever be using a subset of servers can override this to
    # gain a slight decrease in running time.
    TEST_SERVERS = config['lustre_servers']

    # Storage for details of the rest api provided by the manager. Presumes that the api does not change during
    # execution of the whole test suite and so stores the result once in a class variable. A class variable
    # because instances of this class come and go but the api today is constant.
    _chroma_manager_api = None

    _chroma_manager = None

    def setUp(self):
        if config.get('simulator', False):
            # When we're running with the simulator, parts of the simulated
            # Copytools use agent code, and the agent code expects to find
            # a populated agent-side configuration. The safe way to handle
            # this requirement is to use mock to patch in a fresh
            # ConfigStore instance for each test run.
            try:
                from chroma_agent.config_store import ConfigStore
            except ImportError:
                raise ImportError("Cannot import agent, do you need to do a 'setup.py develop' of it?")

            import mock
            import tempfile
            self.mock_config = ConfigStore(tempfile.mkdtemp())
            mock.patch('chroma_agent.config', self.mock_config).start()
            from chroma_agent.action_plugins.settings_management import reset_agent_config, set_agent_config
            reset_agent_config()
            # Allow the worker to create a fifo in /tmp rather than /var/spool
            set_agent_config('copytool_fifo_directory',
                             COPYTOOL_TESTING_FIFO_ROOT)

            try:
                from cluster_sim.simulator import ClusterSimulator
            except ImportError:
                raise ImportError("Cannot import simulator, do you need to do a 'setup.py develop' of it?")

            # The simulator's state directory will be left behind when a test fails,
            # so make sure it has a unique-per-run name
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            state_path = 'simulator_state_%s.%s_%s' % (self.__class__.__name__, self._testMethodName, timestamp)
            if os.path.exists(state_path):
                raise RuntimeError("Simulator state folder already exists at '%s'!" % state_path)

            # Hook up the agent log to a file
            from chroma_agent.agent_daemon import daemon_log
            handler = logging.FileHandler(os.path.join(config.get('log_dir', '/var/log/'), 'chroma_test_agent.log'))
            handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
            daemon_log.addHandler(handler)
            daemon_log.setLevel(logging.DEBUG)

            self.simulator = ClusterSimulator(state_path, config['chroma_managers'][0]['server_http_url'])
            volume_count = max([len(s['device_paths']) for s in self.config_servers])
            self.simulator.setup(len(self.config_servers),
                                 len(self.config_workers),
                                 volume_count,
                                 self.SIMULATOR_NID_COUNT,
                                 self.SIMULATOR_CLUSTER_SIZE,
                                 len(config['power_distribution_units']),
                                 su_size=0)
            self.remote_operations = SimulatorRemoteOperations(self, self.simulator)
            if self.TESTS_NEED_POWER_CONTROL:
                self.simulator.power.start()
        else:
            self.remote_operations = RealRemoteOperations(self)

        # Ensure that all servers are up and available
        for server in self.TEST_SERVERS:
            logger.info("Checking that %s is running and restarting if necessary..." % server['fqdn'])
            self.remote_operations.await_server_boot(server['fqdn'], restart = True)
            logger.info("%s is running" % server['fqdn'])
            self.remote_operations.inject_log_message(server['fqdn'],
                                                      "==== "
                                                      "starting test %s "
                                                      "=====" % self)

        if config.get('reset', True):
            self.reset_cluster()
        elif config.get('soft_reset', True):
            # Reset the manager via the API
            self.wait_until_true(self.api_contactable)
            self.remote_operations.unmount_clients()
            self.api_force_clear()
            self.remote_operations.clear_ha(self.TEST_SERVERS)
            self.remote_operations.clear_lnet_config(self.TEST_SERVERS)

        if config.get('managed'):
            # Erase all volumes if the config does not indicate that there is already
            # a pre-existing file system (in the case of the monitoring only tests).
            for server in self.TEST_SERVERS:
                for path in server.get('device_paths', []):
                    self.remote_operations.erase_block_device(server['fqdn'], path)

            # Ensure that config from previous runs doesn't linger into
            # this one.
            self.remote_operations.remove_config(self.TEST_SERVERS)

            # If there are no configuration options for a given server
            # (e.g. corosync_config), then this is a noop and no config file
            # is written.
            self.remote_operations.write_config(self.TEST_SERVERS)

        # Enable agent debugging
        self.remote_operations.enable_agent_debug(self.TEST_SERVERS)

        self.wait_until_true(self.supervisor_controlled_processes_running)
        self.initial_supervisor_controlled_process_start_times = self.get_supervisor_controlled_process_start_times()

    def tearDown(self):
        if hasattr(self, 'simulator'):
            self.simulator.stop()
            self.simulator.join()

            # Clean up the temp agent config
            import mock
            mock.patch.stopall()
            shutil.rmtree(self.mock_config.path)

            passed = sys.exc_info() == (None, None, None)
            if passed:
                shutil.rmtree(self.simulator.folder)
        else:
            if hasattr(self, 'remote_operations'):
                # Check that all servers are up and available after the test
                down_nodes = []
                for server in self.TEST_SERVERS:
                    if not self.remote_operations.host_contactable(server['address']):
                        down_nodes.append(server['address'])
                    else:
                        self.remote_operations.inject_log_message(
                            server['fqdn'], "==== stopping test %s =====" %
                            self
                        )

                if len(down_nodes):
                    logger.warning("After test, some servers were no longer running: %s" % ", ".join(down_nodes))
                    if not getattr(self, 'down_node_expected', False):
                        raise RuntimeError("AWOL servers after test: %s" %
                                           ", ".join(down_nodes))

        self.assertTrue(self.supervisor_controlled_processes_running())
        self.assertEqual(
            self.initial_supervisor_controlled_process_start_times,
            self.get_supervisor_controlled_process_start_times()
        )

    @property
    def config_servers(self):
        return [s for s in config['lustre_servers']
                if 'worker' not in s.get('profile', "")]

    @property
    def config_workers(self):
        return [w for w in config['lustre_servers']
                if 'worker' in w.get('profile', "")]

    @property
    def chroma_manager(self):
        if self._chroma_manager is None:
            user = config['chroma_managers'][0]['users'][0]
            self._chroma_manager = AuthorizedHttpRequests(user['username'],
                                                          user['password'],
                                                          server_http_url =
                                                          config['chroma_managers'][0]['server_http_url'])
        return self._chroma_manager

    def api_contactable(self):
        try:
            self.chroma_manager.get('/api/system_status/')
            return True
        except requests.ConnectionError:
            return False

    def supervisor_controlled_processes_running(self):
        # Use the api to verify the processes controlled by supervisor are all in a RUNNING state
        try:
            response = self.chroma_manager.get('/api/system_status/')
        except requests.ConnectionError:
            logger.warning("Connection error trying to connect to the manager")
            return False

        self.assertEqual(response.successful, True, response.text)
        system_status = response.json
        non_running_processes = []
        for process in system_status['supervisor']:
            if not process['statename'] == 'RUNNING':
                non_running_processes.append(process)

        if non_running_processes:
            logger.warning("Supervisor processes found not to be running: '%s'" % non_running_processes)
            return False
        else:
            return True

    def get_supervisor_controlled_process_start_times(self):
        response = self.chroma_manager.get('/api/system_status/')
        self.assertEqual(response.successful, True, response.text)
        system_status = response.json
        supervisor_controlled_process_start_times = {}
        for process in system_status['supervisor']:
            supervisor_controlled_process_start_times[process['name']] = process['start']
        return supervisor_controlled_process_start_times

    def _print_command(self, command, disposition="OK"):
        print "COMMAND %s: %s" % (command['id'], disposition)
        print "-----------------------------------------------------------"
        print command
        print ''

        for job_uri in command['jobs']:
            job = self.get_json_by_uri(job_uri)
            job_steps = [self.get_json_by_uri(s) for s in job['steps']]
            if disposition == "FAILED":
                if job['errored']:
                    print "Job %s Errored:" % job['id']
                    print job
                    print ''
                    for step in job_steps:
                        if step['state'] == 'failed':
                            print "Step %s (%s) failed:" % (step['id'], step['description'])
                            print step['console']
                            print step['backtrace']
                            print ''
            elif disposition == "TIMED OUT":
                if job['state'] != "complete":
                    print "Job %s incomplete:" % job['id']
                    print job
                    print ''
                    for step in job_steps:
                        if step['state'] == "incomplete":
                            print "Step %s incomplete:" % step['id']
                            print step
                            print ''
            else:
                print job
                for step in job_steps:
                    print step

    def wait_for_command(self, chroma_manager, command_id, timeout=TEST_TIMEOUT, verify_successful=True):
        logger.debug("wait_for_command: %s" % self.get_json_by_uri('/api/command/%s/' % command_id))
        # TODO: More elegant timeout?
        running_time = 0
        command_complete = False
        while running_time < timeout and not command_complete:
            command = self.get_json_by_uri('/api/command/%s/' % command_id)
            command_complete = command['complete']
            if not command_complete:
                time.sleep(1)
                running_time += 1

        if running_time >= timeout:
            self._print_command(command, "TIMED OUT")
        else:
            logger.debug("command complete: %s" % self.get_json_by_uri('/api/command/%s/' % command_id))

        self.assertTrue(command_complete, command)
        if verify_successful and (command['errored'] or command['cancelled']):
            self._print_command(command, "FAILED")

            self.assertFalse(command['errored'] or command['cancelled'], command)

        return command

    def wait_for_commands(self, chroma_manager, command_ids, timeout=TEST_TIMEOUT, verify_successful = True):
        for command_id in command_ids:
            self.wait_for_command(chroma_manager, command_id, timeout, verify_successful)

    def wait_last_command_complete(self, timeout=TEST_TIMEOUT, verify_successful=True):
        response = self.get_json_by_uri('/api/command/')
        self.wait_for_command(self.chroma_manager, response['meta']['total_count'], timeout, verify_successful)

    def get_list(self, url, args = {}):
        response = self.chroma_manager.get(url, params = args)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json['objects']

    def get_by_uri(self, uri, verify_successful=True):
        response = self.chroma_manager.get(uri)

        if verify_successful:
            self.assertEqual(response.status_code, 200, response.content)

        return response

    def get_json_by_uri(self, uri, verify_successful=True):
        return self.get_by_uri(uri, verify_successful).json

    def wait_for_action(self, victim, timeout=TEST_TIMEOUT, **filters):
        """
        Check victim's available_actions until the desired action is available
        or the timeout is reached, filtering on action keys: class_name, state.
        """
        for index in wait(timeout):
            actions = self.get_json_by_uri(victim['resource_uri'])['available_actions']
            for action in actions:
                if all(action.get(key) == filters[key] for key in filters):
                    return action
        actions = [dict((key, action.get(key)) for key in filters) for action in actions]
        raise AssertionError('{0} not found in {1}'.format(filters, actions))

    def run_command(self, jobs, message = None, verify_successful = True):
        logger.debug("Running %s (%s)" % (jobs, message))
        response = self.chroma_manager.post('/api/command/', body = dict(
            jobs = jobs,
            message = message if message else "Test command"
        ))

        if verify_successful:
            self.assertTrue(response.successful, response.text)
            self.wait_for_command(self.chroma_manager, response.json['id'])
        return response

    def post_by_uri(self, uri, object, verify_successful=True):
        logger.debug("post_by_uri(%s, ...)" % uri)
        response = self.chroma_manager.post(uri, body = object)

        if response.status_code == 204:
            logger.warning("post_by_uri(%s, ...) - no-op" % uri)
            command = None
        else:
            self.assertEquals(response.status_code, 202, response.content)
            command = self.wait_for_command(self.chroma_manager, response.json['command']['id'], verify_successful=verify_successful)

        return command

    def set_value(self, uri, value_name, value, verify_successful=True):
        logger.debug("set_%s %s %s" % (value_name, uri, value))
        object = self.get_json_by_uri(uri)
        object[value_name] = value

        response = self.chroma_manager.put(uri, body = object)
        if response.status_code == 204:
            logger.warning("set_%s %s %s - no-op" % (value_name, uri, value))
            command = None
        else:
            self.assertEquals(response.status_code, 202, response.content)

            # If the state is not a change command will be none and so we have nothing to wait for.
            if response.json['command'] is None:
                command = None
            else:
                command = self.wait_for_command(self.chroma_manager, response.json['command']['id'], verify_successful=verify_successful)

        if verify_successful:
            self.assertValue(uri, value_name, value)

        return command

    def set_state(self, uri, state, verify_successful=True):
        return self.set_value(uri, 'state', state, verify_successful)

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

        data = {'active': True}
        if of_type is not None:
            data['alert_type'] = of_type
        if of_severity is not None:  # Severity should be 'ERROR', 'WARNING', 'INFO'
            data['severity'] = of_severity
        alerts = self.get_list("/api/alert/", data)
        self.assertNotIn(uri, [a['alert_item'] for a in alerts])

    def assertHasAlert(self, uri, of_severity=None, of_type=None):
        data = {'active': True}
        if of_severity is not None:  # Severity should be 'ERROR', 'WARNING', 'INFO'
            data['severity'] = of_severity
        if of_type is not None:
            data['alert_type'] = of_type
        alerts = self.get_list("/api/alert/", data)
        self.assertIn(uri, [a['alert_item'] for a in alerts], [a['alert_item'] for a in alerts])

    def get_alert(self, uri, regex=None, alert_type=None):
        """Given that there is an active alert for object `uri` whose
           message matches `regex`, return it.  Raise an AssertionError
           if no such alert exists"""

        all_alerts = self.get_list("/api/alert/", {'active': True,
                                                   'limit': 0})
        alerts = [a for a in all_alerts if a['alert_item'] == uri]
        if not alerts:
            raise AssertionError("No alerts for object %s (alerts are %s)" % (uri, all_alerts))

        if regex is not None:
            alerts = [a for a in alerts if re.match(regex, a['message'])]
            if not alerts:
                raise AssertionError("No alerts for object %s matching %s (alerts are %s)" % (uri, regex, all_alerts))

        if alert_type is not None:
            alerts = [a for a in alerts if a['alert_type'] == alert_type]
            if not alerts:
                raise AssertionError("No alerts of type %s found (alerts are %s)" % (alert_type, all_alerts))

        if len(alerts) > 1:
            raise AssertionError("Multiple alerts match: %s" % alerts)

        return alerts[0]

    def assertValue(self, uri, value_name, value):
        logger.debug("assertValue %s %s %s" % (value_name, uri, value))
        obj = self.get_json_by_uri(uri)
        self.assertEqual(obj[value_name], str(value))           # Need to convert to string because the value will always come back as a string

    def assertState(self, uri, state):
        self.assertValue(uri, 'state', state)

    def get_filesystem(self, filesystem_id):
        return self.get_json_by_uri("/api/filesystem/%s/" % filesystem_id)

    def get_filesystem_by_name(self, name):
        filesystems = self.get_list("/api/filesystem/")
        try:
            return [f for f in filesystems if f['name'] == name][0]
        except IndexError:
            raise KeyError("No filesystem named %s" % name)

    @property
    def chroma_manager_api(self):
        '''
        Provides the details of the rest api provided by the manager. Presumes that the api does not change during
        execution of the whole test suite and so stores the result once in a class variable. A class variable
        because instances of this class come and go but the api today is constant.

        The call to get_json_by_uri creates quite a lot of useful debug, but it is quite a lot of another advantage of
        only fetching the data once is the we only see the debug once.

        :return: hash of the api
        '''
        if ApiTestCase._chroma_manager_api is None:
            ApiTestCase._chroma_manager_api = self.get_json_by_uri("/api/")

        return ApiTestCase._chroma_manager_api
