import logging
import time

from testconfig import config

from tests.integration.core.api_testcase import ApiTestCase
from tests.integration.core.constants import TEST_TIMEOUT

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class ApiTestCaseWithTestReset(ApiTestCase):
    """
    Adds a few different ways of cleaning out a test cluster.
    """

    def reset_cluster(self):
        """
        Will fully wipe a test cluster:
          - dropping and recreating the chroma manager database
          - unmounting any lustre filesystems from the clients
          - unconfiguring any chroma targets in pacemaker
        """
        self.remote_operations.unmount_clients()
        self.reset_chroma_manager_db()
        # this requires that pacemaker be up which it no longer is until a
        # host is added
        #self.remote_operations.clear_ha()

    def reset_chroma_manager_db(self):
        for chroma_manager in config['chroma_managers']:
            superuser = [u for u in chroma_manager['users'] if u['super']][0]

            # Stop all chroma manager services
            result = self.remote_command(
                chroma_manager['address'],
                'chroma-config stop',
                expected_return_code = None
            )
            if not result.exit_status == 0:
                logger.warn("chroma-config stop failed: rc:%s out:'%s' err:'%s'" % (result.exit_status, result.stdout.read(), result.stderr.read()))

            # Wait for all of the chroma manager services to stop
            running_time = 0
            services = ['chroma-supervisor']
            while services and running_time < TEST_TIMEOUT:
                for service in services:
                    result = self.remote_command(
                        chroma_manager['address'],
                        'service %s status' % service,
                        expected_return_code = None
                    )
                    if result.exit_status == 3:
                        services.remove(service)
                time.sleep(1)
                running_time += 1
            self.assertEqual(services, [], "Not all services were stopped by chroma-config before timeout: %s" % services)

            # Completely nuke the database to start from a clean state.
            self.remote_command(
                chroma_manager['address'],
                'service postgresql stop; rm -fr /var/lib/pgsql/data/*'
            )

            # Run chroma-config setup to recreate the database and start the chroma manager.
            result = self.remote_command(
                chroma_manager['address'],
                "chroma-config setup %s %s localhost &> config_setup.log" % (superuser['username'], superuser['password']),
                expected_return_code = None
            )
            chroma_config_exit_status = result.exit_status
            if not chroma_config_exit_status == 0:
                result = self.remote_command(
                    chroma_manager['address'],
                    "cat config_setup.log"
                )
                self.assertEqual(0, chroma_config_exit_status, "chroma-config setup failed: '%s'" % result.stdout.read())

    def graceful_teardown(self, chroma_manager):
        """
        Removes all filesystems, MGSs, and hosts from chroma via the api.  This is
        not guaranteed to work, and should be done at the end of tests in order to
        verify that the chroma manager instance was in a nice state, rather than
        in setUp/tearDown hooks to ensure a clean system.
        """
        response = chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        self.assertEqual(response.status_code, 200)
        filesystems = response.json['objects']

        self.remote_operations.unmount_clients()

        if len(filesystems) > 0:
            # Remove filesystems
            remove_filesystem_command_ids = []
            for filesystem in filesystems:
                response = chroma_manager.delete(filesystem['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_filesystem_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_filesystem_command_ids)

        # Remove MGT
        response = chroma_manager.get(
            '/api/target/',
            params = {'kind': 'MGT', 'limit': 0}
        )
        mgts = response.json['objects']

        if len(mgts) > 0:
            remove_mgt_command_ids = []
            for mgt in mgts:
                response = chroma_manager.delete(mgt['resource_uri'])
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_mgt_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_mgt_command_ids)

        # Remove hosts
        response = chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                response = chroma_manager.delete(host['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_host_command_ids.append(command_id)

            self.wait_for_commands(chroma_manager, remove_host_command_ids)

        self.assertDatabaseClear()

    def api_force_clear(self):
        """
        Clears the Chroma instance via the API (by issuing ForceRemoveHost
        commands) -- note that this will *not* unconfigure storage servers or
        remove corosync resources: do that separately.
        """

        response = self.chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                command = self.chroma_manager.post("/api/command/", body = {
                    'jobs': [{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host['id']}}],
                    'message': "Test force remove hosts"
                }).json
                remove_host_command_ids.append(command['id'])

            self.wait_for_commands(self.chroma_manager, remove_host_command_ids)

    def assertDatabaseClear(self, chroma_manager = None):
        """
        Checks that the chroma manager API is now clear of filesystems, targets,
        hosts and volumes.
        """

        if chroma_manager is None:
            chroma_manager = self.chroma_manager

        # Verify there are zero filesystems
        response = chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        filesystems = response.json['objects']
        self.assertEqual(0, len(filesystems))

        # Verify there are zero mgts
        response = chroma_manager.get(
            '/api/target/',
            params = {'kind': 'MGT'}
        )
        self.assertTrue(response.successful, response.text)
        mgts = response.json['objects']
        self.assertEqual(0, len(mgts))

        # Verify there are now zero hosts in the database.
        response = chroma_manager.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']
        self.assertEqual(0, len(hosts))

        # Verify there are now zero volumes in the database.
        response = chroma_manager.get(
            '/api/volume/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        volumes = response.json['objects']
        self.assertEqual(0, len(volumes))

    def reset_accounts(self, chroma_manager):
        """Remove any user accounts which are not in the config (such as
        those left hanging by tests)"""

        configured_usernames = [u['username'] for u in config['chroma_managers'][0]['users']]

        response = chroma_manager.get('/api/user/', data = {'limit': 0})
        self.assertEqual(response.status_code, 200)
        for user in response.json['objects']:
            if not user['username'] in configured_usernames:
                chroma_manager.delete(user['resource_uri'])
