import re
import time

from testconfig import config

from tests.utils.http_requests import AuthorizedHttpRequests

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.stats_testcase_mixin import StatsTestCaseMixin


class TestFilesystemDetection(ChromaIntegrationTestCase, StatsTestCaseMixin):
    def setUp(self):
        self.reset_cluster()
        user = config['chroma_managers'][0]['users'][0]
        self.chroma_manager = AuthorizedHttpRequests(user['username'], user['password'],
                server_http_url = config['chroma_managers'][0]['server_http_url'])

        # Attempt to ensure all the targets are mounted for the filesystem.
        for host in config['lustre_servers']:
            self.remote_command(
                host['address'],
                "mount -a",
                expected_return_code = None
            )

    def test_filesystem_detection(self):
        hosts = self.add_hosts([l['address'] for l in config['lustre_servers']])

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
            available_transition_states = [t['state'] for t in host['available_transitions']]
            self.assertListEqual(['removed'], available_transition_states)

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
        self.wait_until_true(lambda: (
            len([t for t in self.get_list('/api/target/') if not t['active_host_name'] == '---']) ==
            len(config['filesystem']['targets'])
        ))

        # Verify target attributes
        targets = self.get_list('/api/target/')
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
        self.assertTrue(mount_command)
        client = config['lustre_clients'].keys()[0]
        self.mount_filesystem(client, config['filesystem']['name'], mount_command)
        try:
            self.remote_command(
                client,
                "rm -rf /mnt/%s/*" % filesystem['name']
            )
            self.exercise_filesystem(client, filesystem)
            self.check_stats(filesystem['id'])
        finally:
            self.unmount_filesystem(client, config['filesystem']['name'])

        # Verify detects target unmount.
        for target in targets:
            target_config = config['filesystem']['targets'][target['name']]
            target_host_config = self.get_host_config(target_config['primary_server'])
            result = self.remote_command(
                target_host_config['address'],
                'mount'
            )
            if re.search("on %s" % target_config['mount_path'], result.stdout.read()):
                self.remote_command(
                    target_host_config['address'],
                    "umount %s" % target_config['mount_path'],
                )
                result = self.remote_command(
                    target_host_config['address'],
                    'mount'
                )
                self.assertNotRegexpMatches(
                    result.stdout.read(),
                    "on %s" % target_config['mount_path']
                )

        # Wait for audit
        time.sleep(30)

        # Verify detected as unmounted
        response = self.chroma_manager.get('/api/target/')
        self.assertEqual(response.successful, True, response.text)
        targets = response.json['objects']
        for target in targets:
            self.assertEqual('unmounted', target['state'], target)

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
