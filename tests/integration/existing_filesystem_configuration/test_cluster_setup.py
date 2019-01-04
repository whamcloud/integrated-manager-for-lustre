from django.utils.unittest import TestCase

from testconfig import config


class TestClusterSetup(TestCase):
    def test_config_import(self):
        self.assertTrue(
            config,
            """

        Empty cluster configuration file. Did you remember to provide one?

        Use '--tc-format=json --tc-file=path/to/your/config.json'
        """,
        )

    def test_config_contains_minimum_components(self):
        # Verify there are enough hosts present for the test
        self.assertGreaterEqual(len(config["lustre_servers"]), 3)
        self.assertGreaterEqual(len(config["lustre_clients"]), 1)
