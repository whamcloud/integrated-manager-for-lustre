import logging

from django.utils.unittest import skip

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from iml_common.lib.util import ExceptionThrowingThread

log = logging.getLogger(__name__)


class TestCorosync(ChromaIntegrationTestCase):
    """Integration tests involving the CorosyncService and DeviceAgent"""

    def setUp(self):
        self.server_configs = []
        super(TestCorosync, self).setUp()

    def _add_corosync_hosts(self, n_hosts):
        # Add the next n_hosts to the installed servers, allows hosts to easily be added incrementally.

        # Quick runtime sanity check.
        assert len(self.TEST_SERVERS[len(self.server_configs) : len(self.server_configs) + n_hosts]) == n_hosts

        self.server_configs.extend(
            self.add_hosts(
                [
                    server["address"]
                    for server in self.TEST_SERVERS[len(self.server_configs) : len(self.server_configs) + n_hosts]
                ]
            )
        )

        def iml_says_pacemakers_running():
            xs = self.get_list("/api/pacemaker_configuration/")
            return all([x["state"] == "started" for x in xs])

        self.wait_until_true(iml_says_pacemakers_running)

    # Check that hosts status is updated
    def _host_on_off_line(self, index, online):
        corosync_configuration = self.get_list(
            "/api/corosync_configuration/", args={"host__fqdn": self.server_configs[index]["fqdn"]}
        )[0]

        return corosync_configuration["corosync_reported_up"] == online

    def test_host_goes_down(self):
        """Test that a host going down results in Alerts

        If a node in a cluster appears as OFFLINE to the corosync agent
        plugin, than the service should raise an Alert.

        In addition to raising an Alert the service makes an attempt to
        save the ManagedHost.corosync_reported_up boolean, but since that is
        not deterministic.  If this test fails, disable those portion of this
        test.
        """
        # Establish baseline for alerts
        start_alerts = self.get_list("/api/alert/", {"active": True, "severity": "WARNING"})

        self._add_corosync_hosts(2)

        # The first update should have said both were online
        def all_hosts_online():
            corosync_configurations = self.get_list("/api/corosync_configuration/")
            return all(
                [corosync_configuration["corosync_reported_up"] for corosync_configuration in corosync_configurations]
            )

        self.wait_until_true(all_hosts_online)

        self.wait_for_assert(
            lambda: self.assertListEqual(
                start_alerts, self.get_list("/api/alert/", {"active": True, "severity": "WARNING"})
            )
        )

        try:
            # Kill the second host
            self.remote_operations.kill_server(self.server_configs[1]["fqdn"])

            self.wait_until_true(lambda: self._host_on_off_line(1, False))
            self.wait_until_true(lambda: self._host_on_off_line(0, True))

            # Check that an alert was created (be specific to the 'is offline' alert
            # to avoid getting confused by 'lost contact' alerts)
            all_alerts = self.get_list("/api/alert/", {"active": True, "severity": "WARNING"})
            offline_alerts = [a for a in all_alerts if "is offline" in a["message"]]
            self.assertEqual(len(offline_alerts), 1, "%s %s" % (len(all_alerts), len(offline_alerts)))
        finally:
            # Now start the second host back up
            self.remote_operations.await_server_boot(self.server_configs[1]["fqdn"], restart=True)

        self.wait_until_true(lambda: self._host_on_off_line(1, True))

    def test_corosync_state_change_1(self):
        """Test state changes on the corosync object and its interaction with the pacemaker object

        Corosync requires to be running but the opposite is not True
        """

        self._add_corosync_hosts(2)

        # Flip the state between started and stopped
        for server in self.server_configs:
            self.set_state(server["corosync_configuration"], "started", "Starting Corosync, Pacemaker is up")
            self.wait_for_assert(
                lambda: self.assertNoAlerts(
                    self.server_configs[0]["corosync_configuration"], of_type="CorosyncStoppedAlert"
                )
            )

            self.set_state(
                server["corosync_configuration"], "stopped", "Stopping Corosync, Pacemaker is up should go down"
            )
            self.wait_for_assert(
                lambda: self.assertHasAlert(server["corosync_configuration"], of_type="CorosyncStoppedAlert")
            )

            self.assertState(server["pacemaker_configuration"], "stopped")

            # Pacemaker should stay stopped even is corosync is started
            self.set_state(server["corosync_configuration"], "started", "Starting Corosync, Pacemaker is down")
            self.wait_for_assert(
                lambda: self.assertNoAlerts(
                    self.server_configs[0]["corosync_configuration"], of_type="CorosyncStoppedAlert"
                )
            )
            self.assertState(server["pacemaker_configuration"], "stopped")

            # Corosync should start when pacemaker starts
            self.set_state(server["corosync_configuration"], "stopped", "Stopping Corosync, Pacemaker is down")
            self.set_state(
                server["pacemaker_configuration"], "started", "Starting Pacemaker, Corosync is down should start"
            )
            self.assertState(server["corosync_configuration"], "started")

            # Corosync should not stop when pacemaker stops
            self.set_state(server["pacemaker_configuration"], "stopped", "Stopping Pacemaker, Corosync is up")
            self.assertState(server["corosync_configuration"], "started")

            # Restart pacemaker or we will get stung by this
            # http://oss.clusterlabs.org/pipermail/pacemaker/2010-January/004387.html
            # No DC means pacemaker doesn't stop. Not an IML but but a pacemaker issue.
            self.set_state(server["pacemaker_configuration"], "started", "Starting Pacemaker, Corosync is up")

    @skip("CorosynNoPeersAlert disabled for now")
    def test_corosync_state_change_2(self):
        """Test state changes on the corosync/pacemaker through a faily random set.
        """

        self._add_corosync_hosts(2)

        def run_states(server):
            states = ["unconfigured", "stopped", "started"]

            for corosync_state in states:
                self.set_state(
                    server["corosync_configuration"],
                    corosync_state,
                    "%s Corosync for %s" % (corosync_state, server["fqdn"]),
                )

                for pacemaker_state in states:
                    self.set_state(
                        server["pacemaker_configuration"],
                        pacemaker_state,
                        "%s Pacemaker for %s" % (pacemaker_state, server["fqnd"]),
                    )

        threads = []

        for server in self.server_configs:
            thread = ExceptionThrowingThread(target=run_states, args=(server,))
            thread.start()
            threads.append(thread)

        ExceptionThrowingThread.wait_for_threads(
            threads
        )  # This will raise an exception if any of the threads raise an exception

    @skip("CorosynNoPeersAlert disabled for now")
    def test_missing_peer(self):
        """Test alert is raised when no peer exists

        Corosync should report an alert when it cannot find a peer. Check this alert is reported.
        """

        # Only one host should be a CorosynNoPeersAlert.
        self._add_corosync_hosts(1)
        self.wait_for_assert(
            lambda: self.assertHasAlert(
                self.server_configs[0]["corosync_configuration"], of_type="CorosyncNoPeersAlert"
            )
        )

        # Two hosts should be no CorosynNoPeersAlert.
        self._add_corosync_hosts(1)
        self.wait_for_assert(
            lambda: self.assertNoAlerts(
                self.server_configs[0]["corosync_configuration"], of_type="CorosyncNoPeersAlert"
            )
        )

    def test_mcast_changes(self):
        self._add_corosync_hosts(2)

        # Ensure no alerts, so that means they are talking.
        self.wait_for_assert(lambda: self.assertNoAlerts(self.server_configs[0]["corosync_configuration"]))

        corosync_ports = [self.remote_operations.get_corosync_port(server["fqdn"]) for server in self.server_configs]

        self.assertEqual(corosync_ports[1:], corosync_ports[:-1])  # Check all corosync ports are the same.

        # Now lets change the mcast_port of the first and see what happens.
        new_mcast_port = corosync_ports[0] - 1

        self.set_value(
            self.server_configs[0]["corosync_configuration"], "mcast_port", new_mcast_port, self.VERIFY_SUCCESS_WAIT
        )
        corosync_ports = [self.remote_operations.get_corosync_port(server["fqdn"]) for server in self.server_configs]
        self.assertNotEqual(corosync_ports[1:], corosync_ports[:-1])  # Check all corosync ports are now different.

        # These nodes can now not see each other. What actually happens today is that they each report themselves online
        # and the other offline so the Alert flips on and off between them. This code validates that flipping.
        # When the behaviour changes (and it should) this code will not pass. When you are at this point look at the gui
        # and watch the alert move between the nodes.
        for server in self.server_configs:
            self.wait_for_assert(lambda: self.assertHasAlert(server["resource_uri"], of_type="HostOfflineAlert"))
            self.wait_for_assert(lambda: self.assertNoAlerts(server["resource_uri"], of_type="HostOfflineAlert"))

        # Now set them back the same - but both as the new value.
        self.set_value(
            self.server_configs[1]["corosync_configuration"], "mcast_port", new_mcast_port, self.VERIFY_SUCCESS_WAIT
        )
        corosync_ports = [self.remote_operations.get_corosync_port(server["fqdn"]) for server in self.server_configs]
        self.assertEqual(corosync_ports[1:], corosync_ports[:-1])  # Check all corosync ports are the same.

        for server in self.server_configs:
            self.wait_for_assert(lambda: self.assertNoAlerts(server["resource_uri"], of_type="HostOfflineAlert"))

    def test_corosync_reverse_dependencies(self):
        filesystem_id = self.create_filesystem_standard(config["lustre_servers"][0:4])

        filesystem = self.get_json_by_uri("/api/filesystem", args={"id": filesystem_id})["objects"][0]

        mgt = self.get_json_by_uri(filesystem["mgt"]["active_host"])

        response = self.set_state_dry_run(mgt["corosync_configuration"], "stopped")

        self.assertEqual(len(response["dependency_jobs"]), 2)

        for required_dependency_job in ["StopTargetJob", "StopPacemakerJob"]:
            next(
                dependency_job
                for dependency_job in response["dependency_jobs"]
                if dependency_job["class"] == required_dependency_job
            )
