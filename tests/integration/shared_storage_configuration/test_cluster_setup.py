import re

from django.utils.unittest import TestCase

from testconfig import config
from tests.integration.core.remote_operations import RealRemoteOperations

import logging

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)


class TestClusterSetup(TestCase):
    @property
    def config_servers(self):
        return [s for s in config["lustre_servers"] if not "worker" in s.get("profile", "")]

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
        self.assertGreaterEqual(len(self.config_servers), 4)

        # Verify we have at least 2 device nodes on each host.
        for host_config in self.config_servers:
            device_paths = host_config["device_paths"]
            self.assertGreaterEqual(len(set(device_paths)), 2)

        self.assertGreaterEqual(len(config["lustre_clients"]), 1)

        # If we indicate failover is set up, ensure we have the proper
        # information configured to test it.
        if config["failover_is_configured"]:
            self.assertGreaterEqual(len(config["hosts"]), 1)
            for lustre_server in self.config_servers:
                self.assertTrue(lustre_server["host"])
                self.assertTrue(lustre_server["destroy_command"])

        # TODO(kelsey): I'd like to add a lot more validation of the cluster.
        #   - devices mounted properly
        #   - can ssh to the hosts
        #   - ...

    def test_multicast_works(self):
        import multiprocessing
        import json

        def run_omping(pipe, server, num_requests):
            response = self.remote_operations.omping(server, self.config_servers, count=num_requests)
            pipe.send(json.dumps(response))

        num_requests = 5
        if config["failover_is_configured"]:
            self.remote_operations = RealRemoteOperations(self)
            pipe_outs = {}
            processes = {}
            # TODO: This is basically pdsh.  Generalize it so that everyone
            #       can use it.
            for server in self.config_servers:
                pout, pin = multiprocessing.Pipe()
                process = multiprocessing.Process(target=run_omping, args=(pin, server, num_requests))
                pipe_outs[server["nodename"]] = pout
                processes[server["nodename"]] = process
                process.start()

            passed = True
            stdouts = []
            for server in self.config_servers:
                omping_result = json.loads(pipe_outs[server["nodename"]].recv())
                # This tests if any of the omping pings failed after the first.
                # It is fairly common for the first multicast packet to be lost
                # while it is still creating the multicast tree.
                pattern = re.compile("\(seq>=2 [1-9][0-9]*%\)")
                if pattern.search(omping_result):
                    passed = False

                # Store the results for aggregate reporting/logging
                stdouts.append(
                    """----------------
%s
-----------------
%s"""
                    % (server["nodename"], omping_result)
                )

                # Make sure each omping process terminates
                processes[server["nodename"]].join()

            aggregate_omping_results = "\n" + " ".join([stdout for stdout in stdouts])
            logger.debug("Omping results: %s" % aggregate_omping_results)

            self.assertTrue(passed, aggregate_omping_results)
