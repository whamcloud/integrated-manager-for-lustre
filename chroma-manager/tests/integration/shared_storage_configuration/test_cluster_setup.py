from django.utils.unittest import TestCase

from testconfig import config


class TestClusterSetup(TestCase):

    def test_config_import(self):
        self.assertTrue(config, """

        Empty cluster configuration file. Did you remember to provide one?

        Use '--tc-format=json --tc-file=path/to/your/config.json'
        """)

    def test_config_contains_minimum_components(self):
        # Verify at least two hosts present
        self.assertGreaterEqual(len(config['lustre_servers']), 2)

        # Verify we have at least 4 device nodes on each host.
        for host_config in config['lustre_servers']:
            device_paths = host_config['device_paths']
            self.assertGreaterEqual(len(set(device_paths)), 4)

        self.assertGreaterEqual(len(config['lustre_clients']), 1)

        # TODO(kelsey): I'd like to add a lot more validation of the cluster.
        #   - devices mounted properly
        #   - can ssh to the hosts
        #   - ...
