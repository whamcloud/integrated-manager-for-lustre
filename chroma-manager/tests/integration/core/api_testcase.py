import datetime
import logging
import shutil
import sys
import time
import os

from testconfig import config
from tests.utils.http_requests import AuthorizedHttpRequests

from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.utility_testcase import UtilityTestCase
from tests.integration.core.remote_operations import  SimulatorRemoteOperations, RealRemoteOperations


logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class ApiTestCase(UtilityTestCase):
    """
    Adds convenience for interacting with the chroma api.
    """

    _chroma_manager = None

    def setUp(self):
        if config.get('simulator', False):
            try:
                from cluster_sim.simulator import ClusterSimulator
            except ImportError:
                raise ImportError("Cannot import simulator, do you need to do a 'setup.py develop' of it?")

            # The simulator's state directory will be left behind when a test fails,
            # so make sure it has a unique-per-run name
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
            state_path = 'simulator_state_%s.%s_%s' % (self.__class__.__name__, self._testMethodName, timestamp)

            # Hook up the agent log to a file
            from chroma_agent.agent_daemon import daemon_log
            handler = logging.FileHandler(os.path.join(config.get('log_dir', '/var/log/'), 'chroma_test_agent.log'))
            handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
            daemon_log.addHandler(handler)
            daemon_log.setLevel(logging.DEBUG)

            # These are sufficient for tests existing at time of writing, could
            # trivially let tests ask for more by looking for these vars at class scope
            SIMULATOR_SERVER_COUNT = 4
            SIMULATOR_VOLUME_COUNT = 8
            SIMULATOR_NID_COUNT = 1
            SIMULATOR_SERVER_PSU_COUNT = 1
            SIMULATOR_CLUSTER_SIZE = 4
            self.simulator = ClusterSimulator(state_path, config['chroma_managers'][0]['server_http_url'])
            self.simulator.setup(SIMULATOR_SERVER_COUNT, SIMULATOR_VOLUME_COUNT,
                                 SIMULATOR_NID_COUNT, SIMULATOR_CLUSTER_SIZE, SIMULATOR_SERVER_PSU_COUNT)
            self.remote_operations = SimulatorRemoteOperations(self.simulator)
        else:
            self.remote_operations = RealRemoteOperations(self)

        # Ensure that all servers are up and available
        for server in config['lustre_servers']:
            logger.info("Checking that %s is running and restarting if necessary..." % server['fqdn'])
            self.remote_operations.await_server_boot(server['fqdn'], restart = True)
            logger.info("%s is running" % server['fqdn'])

        reset = config.get('reset', True)
        if reset:
            self.reset_cluster()
        else:
            # Reset the manager via the API
            self.remote_operations.unmount_clients()
            self.api_force_clear()
            self.remote_operations.clear_ha()

    def tearDown(self):
        if hasattr(self, 'simulator'):
            self.simulator.stop()
            self.simulator.join()

            passed = sys.exc_info() == (None, None, None)
            if passed:
                shutil.rmtree(self.simulator.folder)
        else:
            # Check that all servers are up and available after the test
            down_nodes = []
            for server in config['lustre_servers']:
                if not self.remote_operations._host_contactable(server['fqdn']):
                    down_nodes.append(server['fqdn'])

            if len(down_nodes):
                logger.warning("After test, some servers were no longer running: %s" % ", ".join(down_nodes))
                if not getattr(self, 'down_node_expected', False):
                    raise RuntimeError("AWOL servers after test: %s" % ", ".join(down_nodes))

    @property
    def chroma_manager(self):
        if self._chroma_manager is None:
            user = config['chroma_managers'][0]['users'][0]
            self._chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
                server_http_url = config['chroma_managers'][0]['server_http_url'])
        return self._chroma_manager

    def wait_for_command(self, chroma_manager, command_id, timeout=TEST_TIMEOUT, verify_successful=True):
        logger.debug("wait_for_command: %s" % self.get_by_uri('/api/command/%s/' % command_id))
        # TODO: More elegant timeout?
        running_time = 0
        command_complete = False
        while running_time < timeout and not command_complete:
            command = self.get_by_uri('/api/command/%s/' % command_id)
            command_complete = command['complete']
            if not command_complete:
                time.sleep(1)
                running_time += 1

        self.assertTrue(command_complete, command)
        if verify_successful and (command['errored'] or command['cancelled']):
            print "COMMAND %s FAILED:" % command['id']
            print "-----------------------------------------------------------"
            print command
            print ''

            for job_uri in command['jobs']:
                response = chroma_manager.get(job_uri)
                self.assertTrue(response.successful, response.text)
                job = response.json
                if job['errored']:
                    print "Job %s Errored:" % job['id']
                    print job
                    print ''
                    for step_uri in job['steps']:
                        response = chroma_manager.get(step_uri)
                        self.assertTrue(response.successful, response.text)
                        step = response.json
                        if step['state'] == 'failed':
                            print "Step %s failed:" % step['id']
                            print step['console']
                            print step['backtrace']
                            print ''

            self.assertFalse(command['errored'] or command['cancelled'], command)

    def wait_for_commands(self, chroma_manager, command_ids, timeout=TEST_TIMEOUT, verify_successful = True):
        for command_id in command_ids:
            self.wait_for_command(chroma_manager, command_id, timeout, verify_successful)

    def get_list(self, url, args = {}):
        response = self.chroma_manager.get(url, params = args)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json['objects']

    def get_by_uri(self, uri):
        response = self.chroma_manager.get(uri)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json

    def set_state(self, uri, state):
        logger.debug("set_state %s %s" % (uri, state))
        object = self.get_by_uri(uri)
        object['state'] = state

        response = self.chroma_manager.put(uri, body = object)
        if response.status_code == 204:
            logger.warning("set_state %s %s - no-op" % (uri, state))
        else:
            self.assertEquals(response.status_code, 202, response.content)
            self.wait_for_command(self.chroma_manager, response.json['command']['id'])

        self.assertState(uri, state)

    def assertNoAlerts(self, uri):
        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertNotIn(uri, [a['alert_item'] for a in alerts])

    def assertHasAlert(self, uri):
        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertIn(uri, [a['alert_item'] for a in alerts])

    def assertState(self, uri, state):
        logger.debug("assertState %s %s" % (uri, state))
        obj = self.get_by_uri(uri)
        self.assertEqual(obj['state'], state)

    def get_filesystem(self, filesystem_id):
        return self.get_by_uri("/api/filesystem/%s/" % filesystem_id)
