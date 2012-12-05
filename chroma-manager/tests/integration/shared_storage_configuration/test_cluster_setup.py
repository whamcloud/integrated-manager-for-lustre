from django.utils.unittest import TestCase

from testconfig import config


class TestClusterSetup(TestCase):

    def test_config_import(self):
        self.assertTrue(config, """

        Empty cluster configuration file. Did you remember to provide one?

        Use '--tc-format=json --tc-file=path/to/your/config.json'
        """)

    def test_config_contains_minimum_components(self):
        # Verify there are enough hosts present for the test
        self.assertGreaterEqual(len(config['lustre_servers']), 4)

        # Verify we have at least 2 device nodes on each host.
        for host_config in config['lustre_servers']:
            device_paths = host_config['device_paths']
            self.assertGreaterEqual(len(set(device_paths)), 2)

        self.assertGreaterEqual(len(config['lustre_clients']), 1)

        # If we indicate failover is set up, ensure we have the proper
        # information configured to test it.
        if config['failover_is_configured']:
            if not config.get('simulator', False):
                self.assertGreaterEqual(len(config['hosts']), 1)
                for lustre_server in config['lustre_servers']:
                    self.assertTrue(lustre_server['host'])
                    self.assertTrue(lustre_server['destroy_command'])

        # TODO(kelsey): I'd like to add a lot more validation of the cluster.
        #   - devices mounted properly
        #   - can ssh to the hosts
        #   - ...
