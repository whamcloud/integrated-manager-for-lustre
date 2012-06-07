import time

from testconfig import config

from tests.utils.http_requests import AuthorizedHttpRequests
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.testcases import ChromaIntegrationTestCase


class TestFilesystemDetection(ChromaIntegrationTestCase):
    def setUp(self):
        user = config['chroma_managers'][0]['users'][0]
        self.chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
                server_http_url = config['chroma_managers'][0]['server_http_url'])
        self.reset_cluster(self.chroma_manager)

        # Attempt to ensure all the targets are mounted for the filesystem.
        for host in config['lustre_servers']:
            self.remote_command(
                host['address'],
                "mount -a",
                expected_return_code = None
            )

    def test_filesystem_detection(self):
        # HACKAROUND FOR HYD-1112. Replace with call in this comment when fixed.
        # hosts = self.add_hosts([l['address'] for l in config['lustre_servers']])
        addresses = [l['address'] for l in config['lustre_servers']]
        host_create_command_ids = []
        for host_address in addresses:
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
        self.wait_for_commands(self.chroma_manager, host_create_command_ids, verify_successful = False)

        # Verify there are now n hosts in the database.
        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']
        self.assertEqual(len(addresses), len(hosts))

        # Wait for all hosts to migrate to lnet_up status. (Lnet is really up before
        # this test even starts, but this is part of the hackaround.)
        lnet_up = False
        running_time = 0
        while not lnet_up and running_time < TEST_TIMEOUT:
            lnet_up = True
            for host in hosts:
                try:
                    self.set_state(
                        '/api/host/%s/' % host['id'],
                        'lnet_up'
                    )
                except AssertionError:
                    lnet_up = False
            running_time += 1
            time.sleep(1)
        # END Hackaround

        # Verify hosts are immutable
        response = self.chroma_manager.get(
            '/api/host/',
        )
        self.assertEqual(response.successful, True, response.text)
        hosts = response.json['objects']
        self.assertEqual(len(config['lustre_servers']), len(hosts))
        for host in hosts:
            self.assertTrue(host['immutable_state'])
            available_job_classes = [j['class_name'] for j in host['available_jobs']]
            self.assertIn('ForceRemoveHostJob', available_job_classes)
            self.assertListEqual([], host['available_transitions'])

        # Issue command to detect existing filesystem
        response = self.chroma_manager.post(
            '/api/command/',
            body = {
                'message': 'Detecting filesystems',
                'jobs': [{
                    'class_name': 'DetectTargetsJob',
                    'args': {},
                }],
            }
        )
        self.assertEqual(response.successful, True, response.text)
        command = response.json
        self.wait_for_command(self.chroma_manager, command['id'])

        # Verify it detected the filesystem
        response = self.chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        self.assertEqual(response.successful, True, response.text)
        filesystems = response.json['objects']
        self.assertEqual(len(filesystems), 1)
        filesystem = filesystems[0]
        self.assertEqual(config['filesystem']['name'], filesystem['name'])
        self.assertTrue(filesystem['immutable_state'])
        available_states = [t['state'] for t in filesystem['available_transitions']]
        self.assertIn('forgotten', available_states)
        self.assertNotIn('removed', available_states)

        # Wait for active_host_name to get set on all of the targets
        targets = []
        targets_active = False
        running_time = 0
        while not targets_active and running_time < TEST_TIMEOUT:
            response = self.chroma_manager.get('/api/target/')
            self.assertEqual(response.successful, True, response.text)
            targets = response.json['objects']
            self.assertEqual(len(config['filesystem']['targets']), len(targets))

            targets_active = True
            for target in targets:
                if target['active_host_name'] == '---':
                    targets_active = False
                    break
            time.sleep(1)
            running_time += 1

        self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for actibe_host_name to be set on all targets.")

        # Verify target attributes
        for target in targets:
            target_config = config['filesystem']['targets'][target['name']]
            target_host_config = self.get_host_config(target_config['primary_server'])
            self.assertEqual(target_config['kind'], target['kind'])
            self.assertEqual(target_host_config['fqdn'], target['primary_server_name'])
            self.assertEqual(target_host_config['fqdn'], target['active_host_name'])
            self.assertTrue(target['immutable_state'])
            self.assertEqual('mounted', target['state'])

        # Verify filesystem is available
        response = self.chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        self.assertEqual(response.successful, True, response.text)
        filesystems = response.json['objects']
        self.assertEqual(len(filesystems), 1)
        filesystem = filesystems[0]
        self.assertEqual('available', filesystem['state'])

        # Verify a client can use the filesystem using the mount command provided
        mount_command = filesystem['mount_command']
        client = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client, config['filesystem']['name'], mount_command)
        try:
            self.exercise_filesystem(client, config['filesystem']['name'])
        finally:
            self.unmount_filesystem(client, config['filesystem']['name'])

        # Verify detects target unmount.
        for target in targets:
            target_config = config['filesystem']['targets'][target['name']]
            target_host_config = self.get_host_config(target_config['primary_server'])
            self.remote_command(
                target_host_config['address'],
                "umount %s" % target_config['mount_path']
            )

        # Wait for audit
        time.sleep(30)

        # Verify detected as unmounted
        response = self.chroma_manager.get('/api/target/')
        self.assertEqual(response.successful, True, response.text)
        targets = response.json['objects']
        for target in targets:
            self.assertEqual('unmounted', target['state'])

        # Verify filesystem is unavailable
        response = self.chroma_manager.get(
            '/api/filesystem/',
            params = {'limit': 0}
        )
        self.assertEqual(response.successful, True, response.text)
        filesystems = response.json['objects']
        self.assertEqual(len(filesystems), 1)
        filesystem = filesystems[0]
        self.assertEqual('stopped', filesystem['state'])

        # Remount all targets
        for host in config['lustre_servers']:
            self.remote_command(
                host['address'],
                "mount -a"
            )

        # Wait for audit
        time.sleep(30)

        # Verify all targets detected as mounted
        response = self.chroma_manager.get('/api/target/')
        self.assertEqual(response.successful, True, response.text)
        targets = response.json['objects']
        for target in targets:
            self.assertEqual('mounted', target['state'])
