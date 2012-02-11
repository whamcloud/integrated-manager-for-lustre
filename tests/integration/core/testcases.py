import paramiko
import re
import time

from django.utils.unittest import TestCase

from testconfig import config

from tests.integration.core.constants import TEST_TIMEOUT


class ChromaIntegrationTestCase(TestCase):

    def reset_cluster(self, hydra_server):
        response = hydra_server.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        filesystems = response.json['objects']

        if len(filesystems) > 0:
            # Unmount filesystems
            for client in config['lustre_clients'].keys():
                for filesystem in filesystems:
                    self.unmount_filesystem(client, filesystem['name'])

            # Remove filesystems
            remove_filesystem_command_ids = []
            for filesystem in filesystems:
                response = hydra_server.delete(filesystem['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_filesystem_command_ids.append(command_id)

            self.wait_for_commands(hydra_server, remove_filesystem_command_ids)

        # Verify there are now zero filesystems
        response = hydra_server.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        filesystems = response.json['objects']
        self.assertEqual(0, len(filesystems))

        # Remove MGT
        response = hydra_server.get(
            '/api/target/',
            params = {'kind': 'MGT', 'limit': 0}
        )
        mgts = response.json['objects']

        if len(mgts) > 0:
            remove_mgt_command_ids = []
            for mgt in mgts:
                response = hydra_server.delete(mgt['resource_uri'])
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_mgt_command_ids.append(command_id)

            self.wait_for_commands(hydra_server, remove_mgt_command_ids)

        # Verify there are now zero mgts
        response = hydra_server.get(
            '/api/target/',
            params = {'kind': 'MGT'}
        )
        mgts = response.json['objects']
        self.assertEqual(0, len(mgts))

        response = hydra_server.get(
            '/api/host/',
            params = {'limit': 0}
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']

        if len(hosts) > 0:
            # Verify mgs and fs targets not in pacemaker config for hosts
            for host in hosts:
                for filesystem in filesystems:
                    stdin, stdout, stderr = self.remote_command(
                        host['address'],
                        'crm configure show'
                    )
                    configuration = stdout.read()
                    self.assertNotRegexpMatches(
                        configuration,
                        "location [^\n]* %s\n" % host['nodename']
                    )
                    self.assertNotRegexpMatches(
                        configuration,
                        "primitive %s-" % filesystem['name']
                    )
                    self.assertNotRegexpMatches(
                        configuration,
                        "id=\"%s-" % filesystem['name']
                    )

            # Remove hosts
            remove_host_command_ids = []
            for host in hosts:
                response = hydra_server.delete(host['resource_uri'])
                self.assertTrue(response.successful, response.text)
                command_id = response.json['command']['id']
                self.assertTrue(command_id)
                remove_host_command_ids.append(command_id)

            self.wait_for_commands(hydra_server, remove_host_command_ids)

        # Verify there are now zero hosts in the database.
        response = hydra_server.get(
            '/api/host/',
        )
        self.assertTrue(response.successful, response.text)
        hosts = response.json['objects']
        self.assertEqual(0, len(hosts))

    def wait_for_command(self, hydra_server, command_id, timeout=TEST_TIMEOUT, verify_successful=True):
        # TODO: More elegant timeout?
        running_time = 0
        command_complete = False
        while running_time < timeout and not command_complete:
            response = hydra_server.get(
                '/api/command/%s/' % command_id,
            )
            self.assertTrue(response.successful, response.text)
            command = response.json
            command_complete = command['complete']
            if not command_complete:
                time.sleep(1)
                running_time += 1

        self.assertTrue(command_complete, command)
        if verify_successful:
            self.assertFalse(command['errored'] or command['cancelled'], command)

    def wait_for_commands(self, hydra_server, command_ids, timeout=TEST_TIMEOUT):
        for command_id in command_ids:
            self.wait_for_command(hydra_server, command_id, timeout)

    def remote_command(self, server, command, expected_return_code=0):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server)
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
        response = self.hydra_server.get(
            '/api/volume_node/'
        )
        self.assertTrue(response.successful, response.text)
        lun_nodes = response.json['objects']

        response = self.hydra_server.get(
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
                config_device_paths = config['lustre_servers'][host_address]['device_paths']
                config_paths = [str(p) for p in config_device_paths]

                self.assertTrue(lun_node['path'] in config_paths,
                    "Path: %s Config Paths: %s" % (
                        lun_node['path'], config_device_paths)
                )

    def create_filesystem(self, verify_successful=True, **kwargs):
        for param in ['mgt_id', 'mgt_lun_id', 'conf_params']:
            # some params can be empty strings, but have to be present.
            if not param in kwargs:
                kwargs[param] = ''

        response = self.hydra_server.post(
            '/api/filesystem/',
            body = kwargs
        )

        self.assertTrue(response.successful, response.text)
        filesystem_id = response.json['filesystem']['id']
        command_id = response.json['command']['id']

        self.wait_for_command(self.hydra_server, command_id,
            verify_successful=verify_successful)

        response = self.hydra_server.get(
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
                "primitive %s-" % kwargs['name']
            )
            self.assertRegexpMatches(
                configuration,
                "id=\"%s-" % kwargs['name']
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
        else:
            print "Unmount requested for %s, but %s not mounted." % (
                filesystem_name, filesystem_name)

    def exercise_filesystem(self, client, filesystem_name):
        # TODO: Expand on this. Perhaps use existing lustre client tests.
        self.remote_command(
            client,
            "dd if=/dev/zero of=/mnt/%s/test.dat bs=1K count=500K" % filesystem_name
        )
