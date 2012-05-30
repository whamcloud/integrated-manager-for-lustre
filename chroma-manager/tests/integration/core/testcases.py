import logging
import paramiko
import re
import socket
import time

from django.utils.unittest import TestCase

from testconfig import config

from tests.integration.core.constants import TEST_TIMEOUT

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler('test.log'))


class ChromaIntegrationTestCase(TestCase):
    def reset_accounts(self, chroma_manager):
        """Remove any user accounts which are not in the config (such as
        those left hanging by tests)"""

        configured_usernames = [u['username'] for u in config['chroma_managers'][0]['users']]

        response = chroma_manager.get('/api/user/', data = {'limit': 0})
        self.assertEqual(response.status_code, 200)
        for user in response.json['objects']:
            if not user['username'] in configured_usernames:
                chroma_manager.delete(user['resource_uri'])

    def erase_volumes(self):
        for server in config['lustre_servers']:
            for device in server['device_paths']:
                self.remote_command(server['address'], "dd if=/dev/zero of=%s bs=4M count=1" % device)

    def reset_cluster(self, chroma_manager):
        response = chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        filesystems = response.json['objects']

        if len(filesystems) > 0:
            # Unmount filesystems
            for client in config['lustre_clients'].keys():
                for filesystem in filesystems:
                    self.unmount_filesystem(client, filesystem['name'])

        try:
            self.graceful_teardown(chroma_manager)
        except Exception:
            self.force_teardown(chroma_manager)

    def reset_chroma_manager_db(self, user):
        for chroma_manager in config['chroma_managers']:
            self.remote_command(
                chroma_manager['address'],
                'chroma-config stop'
            )
            self.remote_command(
                chroma_manager['address'],
                'echo "drop database chroma; create database chroma;" | mysql -u root'
            )

            self.remote_command(
                chroma_manager['address'],
                """
chroma-config setup >config_setup.log <<EOF
%s
nobody@whamcloud.com
%s
%s
EOF
                """ % (user['username'], user['password'], user['password'])
            )
            self.remote_command(
                chroma_manager['address'],
                "chroma-config start"
            )
            self.remote_command(
                chroma_manager['address'],
                "chroma-config validate"
            )

    def force_teardown(self, chroma_manager):
        response = chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        if len(hosts) > 0:
            remove_host_command_ids = []
            for host in hosts:
                command = chroma_manager.post("/api/command/", body = {
                    'jobs': [{'class_name': 'ForceRemoveHostJob', 'args': {'host_id': host['id']}}],
                    'message': "Test force remove hosts"
                }).json
                remove_host_command_ids.append(command['id'])

            self.wait_for_commands(chroma_manager, remove_host_command_ids)

        for server in config['lustre_servers']:
            address = server['address']
            self.remote_command(address, "chroma-agent clear-targets")

        self.verify_cluster_not_configured(chroma_manager)

    def graceful_teardown(self, chroma_manager):
        """Remove all Filesystems, MGTs, and Hosts"""
        response = chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        filesystems = response.json['objects']

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

        self.verify_cluster_not_configured(chroma_manager)

    def verify_cluster_not_configured(self, chroma_manager):
        """
        Checks that the database and the hosts specified in the config
        do not have (unremoved) targets for the filesystems specified.
        """
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
        # TEMPORARILY COMMENTED OUT DUE TO HYD-1143.
        #response = self.chroma_manager.get(
        #    '/api/volume/',
        #    params = {'limit': 0}
        #)
        #self.assertTrue(response.successful, response.text)
        #volumes = response.json['objects']
        #self.assertEqual(0, len(volumes))

        for host in config['lustre_servers']:
            # Verify mgs and fs targets not in pacemaker config for hosts
            # TODO: sort out host address and host nodename
            stdin, stdout, stderr = self.remote_command(
                host['address'],
                'crm configure show'
            )
            configuration = stdout.read()
            self.assertNotRegexpMatches(
                configuration,
                "location [^\n]* %s\n" % host['nodename']
            )

    def wait_for_command(self, chroma_manager, command_id, timeout=TEST_TIMEOUT, verify_successful=True):
        logger.debug("wait_for_command %s" % command_id)
        # TODO: More elegant timeout?
        running_time = 0
        command_complete = False
        while running_time < timeout and not command_complete:
            response = chroma_manager.get(
                '/api/command/%s/' % command_id,
            )
            self.assertTrue(response.successful, response.text)
            command = response.json
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
                        if step['exception'] and not step['exception'] == 'None':
                            print "Step %s Errored:" % step['id']
                            print step['console']
                            print step['exception']
                            print step['backtrace']
                            print ''

            self.assertFalse(command['errored'] or command['cancelled'], command)

    def wait_for_commands(self, chroma_manager, command_ids, timeout=TEST_TIMEOUT):
        for command_id in command_ids:
            self.wait_for_command(chroma_manager, command_id, timeout)

    def remote_command(self, server, command, expected_return_code=0):
        logger.debug("remote_command[%s]: %s" % (server, command))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, **{'username': 'root'})
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(TEST_TIMEOUT)
        channel.exec_command(command)
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        stderr = channel.makefile_stderr()
        if expected_return_code is not None:
            exit_status = channel.recv_exit_status()
            self.assertEqual(exit_status, expected_return_code, stderr.read())
        return stdin, stdout, stderr

    def verify_usable_luns_valid(self, usable_luns, num_luns_needed):

        # Assert meets the minimum number of devices needed for this test.
        self.assertGreaterEqual(len(usable_luns), num_luns_needed)

        # Verify no extra devices not in the config visible.
        response = self.chroma_manager.get(
            '/api/volume_node/'
        )
        self.assertTrue(response.successful, response.text)
        lun_nodes = response.json['objects']

        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        host_id_to_address = dict((h['id'], h['address']) for h in hosts)
        usable_luns_ids = [l['id'] for l in usable_luns]

        for lun_node in lun_nodes:
            if lun_node['volume_id'] in usable_luns_ids:

                # Create a list of usable device paths for the host of the
                # current lun node as listed in the config.
                host_id = lun_node['host_id']
                host_address = host_id_to_address[host_id]
                host_config = [l for l in config['lustre_servers'] if l['address'] == host_address]
                self.assertEqual(1, len(host_config))
                host_config = host_config[0]
                config_device_paths = host_config['device_paths']
                config_paths = [str(p) for p in config_device_paths]

                self.assertTrue(lun_node['path'] in config_paths,
                    "Path: %s Config Paths: %s" % (
                        lun_node['path'], config_device_paths)
                )

    def set_volume_mounts(self, volume, primary_host_id, secondary_host_id):
        primary_volume_node_id = None
        secondary_volume_node_id = None
        for node in volume['volume_nodes']:
            if node['host_id'] == int(primary_host_id):
                primary_volume_node_id = node['id']
            elif node['host_id'] == int(secondary_host_id):
                secondary_volume_node_id = node['id']

        self.assertTrue(primary_volume_node_id, volume)
        self.assertTrue(secondary_volume_node_id, volume)

        response = self.chroma_manager.put(
            "/api/volume/%s/" % volume['id'],
            body = {
                "id": volume['id'],
                "nodes": [
                    {
                        "id": secondary_volume_node_id,
                        "primary": False,
                        "use": True,
                    },
                    {
                        "id": primary_volume_node_id,
                        "primary": True,
                        "use": True,
                    }
                ]
            }
        )
        self.assertTrue(response.successful, response.text)

    def verify_volume_mounts(self, volume, expected_primary_host_id, expected_secondary_host_id):
        for node in volume['volume_nodes']:
            if node['primary']:
                self.assertEqual(node['host_id'], int(expected_primary_host_id))
            elif node['use']:
                self.assertEqual(node['host_id'], int(expected_secondary_host_id))

    def create_filesystem(self, filesystem, verify_successful = True):
        response = self.chroma_manager.post(
            '/api/filesystem/',
            body = filesystem
        )

        self.assertTrue(response.successful, response.text)
        filesystem_id = response.json['filesystem']['id']
        command_id = response.json['command']['id']

        self.wait_for_command(self.chroma_manager, command_id,
            verify_successful=verify_successful)

        response = self.chroma_manager.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        # Verify mgs and fs targets in pacemaker config for hosts
        for host in hosts:
            stdin, stdout, stderr = self.remote_command(
                host['address'],
                'crm configure show'
            )
            configuration = stdout.read()
            self.assertRegexpMatches(
                configuration,
                "location [^\n]* %s\n" % host['nodename']
            )
            self.assertRegexpMatches(
                configuration,
                "primitive %s-" % filesystem['name']
            )
            self.assertRegexpMatches(
                configuration,
                "id=\"%s-" % filesystem['name']
            )

        return filesystem_id

    def mount_filesystem(self, client, filesystem_name, mount_command, expected_return_code=0):
        self.remote_command(
            client,
            "mkdir -p /mnt/%s" % filesystem_name,
            expected_return_code = None  # May fail if already exists. Keep going.
        )

        self.remote_command(
            client,
            mount_command
        )

        stdin, stdout, stderr = self.remote_command(
            client,
            'mount'
        )
        self.assertRegexpMatches(
            stdout.read(),
            " on /mnt/%s " % filesystem_name
        )

    def unmount_filesystem(self, client, filesystem_name):
        stdin, stdout, stderr = self.remote_command(
            client,
            'mount'
        )
        if re.search(" on /mnt/%s " % filesystem_name, stdout.read()):
            self.remote_command(
                client,
                "umount /mnt/%s" % filesystem_name,
            )
            stdin, stdout, stderr = self.remote_command(
                client,
                'mount'
            )
            self.assertNotRegexpMatches(
                stdout.read(),
                " on /mtn/%s " % filesystem_name
            )

    def exercise_filesystem(self, client, filesystem_name):
        # TODO: Expand on this. Perhaps use existing lustre client tests.
        # TODO: read back the size of the filesystem first and don't exceed its size
        self.remote_command(
            client,
            "dd if=/dev/zero of=/mnt/%s/test.dat bs=1K count=100K" % filesystem_name
        )

    def _check_targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts, assert_true):
        response = self.chroma_manager.get(
            '/api/target/',
            params = {
                'filesystem_id': filesystem_id,
            }
        )
        self.assertTrue(response.successful, response.text)
        targets = response.json['objects']

        for target in targets:
            target_volume_url = target['volume']
            response = self.chroma_manager.get(target_volume_url)
            self.assertTrue(response.successful, response.text)
            target_volume_id = response.json['id']
            if target_volume_id in volumes_to_expected_hosts:
                expected_host = volumes_to_expected_hosts[target_volume_id]
                if assert_true:
                    self.assertEqual(expected_host, target['active_host_name'])
                else:
                    if not expected_host == target['active_host_name']:
                        return False

        return True

    def add_hosts(self, addresses):
        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        pre_existing_hosts = response.json['objects']

        host_create_command_ids = []
        for host_address in addresses:
            response = self.chroma_manager.post(
                '/api/test_host/',
                body = {'address': host_address}
            )
            self.assertEqual(response.successful, True, response.text)
            # FIXME: check the body of the response to test_host to see
            # if it actually reported contactability correctly

            response = self.chroma_manager.post(
                '/api/host/',
                body = {'address': host_address}
            )
            self.assertEqual(response.successful, True, response.text)
            host_id = response.json['host']['id']
            host_create_command_ids.append(response.json['command']['id'])
            self.assertTrue(host_id)

            response = self.chroma_manager.get(
                '/api/host/%s/' % host_id,
            )
            self.assertEqual(response.successful, True, response.text)
            host = response.json
            self.assertEqual(host['address'], host_address)

        # Wait for the host setup and device discovery to complete
        self.wait_for_commands(self.chroma_manager, host_create_command_ids)

        # Verify there are now two hosts in the database.
        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']
        self.assertEqual(len(addresses), len(hosts) - len(pre_existing_hosts))
        self.assertListEqual([h['state'] for h in hosts], ['lnet_up'] * len(hosts))

        new_hosts = [h for h in hosts if h['id'] not in [s['id'] for s in pre_existing_hosts]]

        return new_hosts

    def get_usable_volumes(self):
        response = self.chroma_manager.get(
            '/api/volume/',
            params = {'category': 'usable', 'limit': 0}
        )
        self.assertEqual(response.successful, True, response.text)
        return response.json['objects']

    def get_shared_volumes(self):
        # Volumes suitable for shared storage test
        # (i.e. they have both a primary and a secondary node)
        volumes = self.get_usable_volumes()

        ha_volumes = []
        for v in volumes:
            has_primary = len([node for node in v['volume_nodes'] if node['primary']]) == 1
            has_two = len([node for node in v['volume_nodes'] if node['use']]) >= 2
            if has_primary and has_two:
                ha_volumes.append(v)

        return ha_volumes

    def targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts):
        return self._check_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_to_expected_hosts, assert_true = False)

    def verify_targets_for_volumes_started_on_expected_hosts(self, filesystem_id, volumes_to_expected_hosts):
        return self._check_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_to_expected_hosts, assert_true = True)

    def get_list(self, url, args = {}):
        response = self.chroma_manager.get(url, params = args)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json['objects']

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

    def get_by_uri(self, uri):
        response = self.chroma_manager.get(uri)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json

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

    def create_filesystem_simple(self):
        """The simplest possible filesystem on a single server"""
        self.add_hosts([config['lustre_servers'][0]['address']])

        ha_volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(ha_volumes), 4)

        mgt_volume = ha_volumes[0]
        mdt_volume = ha_volumes[1]
        ost_volumes = [ha_volumes[2]]
        return self.create_filesystem(
                {
                'name': 'testfs',
                'mgt': {'volume_id': mgt_volume['id']},
                'mdt': {
                    'volume_id': mdt_volume['id'],
                    'conf_params': {}
                },
                'osts': [{
                    'volume_id': v['id'],
                    'conf_params': {}
                } for v in ost_volumes],
                'conf_params': {}
            }
        )

    def failover(self, primary_host, secondary_host, filesystem_id, volumes_expected_hosts_in_normal_state, volumes_expected_hosts_in_failover_state):
        # Attach configurations to primary host so we can retreive information
        # about its vmhost and hwo to destroy it.
        for lustre_server in config['lustre_servers']:
            if lustre_server['nodename'] == primary_host['nodename']:
                primary_host['config'] = lustre_server

        # "Pull the plug" on the primary lustre server
        self.remote_command(
            primary_host['config']['host'],
            primary_host['config']['destroy_command']
        )

        # Wait for failover to occur
        running_time = 0
        while running_time < TEST_TIMEOUT and not self.targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state):
            time.sleep(1)
            running_time += 1

        self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for failover")
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

        self.wait_for_host_to_boot(
            booting_host = primary_host,
            available_host = secondary_host
        )

        # Verify did not auto-failback
        self.verify_targets_for_volumes_started_on_expected_hosts(filesystem_id, volumes_expected_hosts_in_failover_state)

    def wait_for_host_to_boot(self, booting_host, available_host):
        # Wait for the stonithed server to come back online
        running_time = 0
        while running_time < TEST_TIMEOUT:
            try:
                #TODO: Better way to check this?
                _, stdout, _ = self.remote_command(
                    booting_host['nodename'],
                    "echo 'Checking if node is ready to receive commands.'"
                )
            except socket.error:
                continue
            finally:
                time.sleep(3)
                running_time += 3

            # Verify other host knows it is no longer offline
            _, stdout, _ = self.remote_command(
                available_host['nodename'],
                "crm node show %s" % booting_host['nodename']
            )
            node_status = stdout.read()
            if not re.search('offline', node_status):
                break

        self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for host to come back online.")
        _, stdout, _ = self.remote_command(
            available_host['nodename'],
            "crm node show %s" % booting_host['nodename']
        )
        self.assertNotRegexpMatches(stdout.read(), 'offline')
