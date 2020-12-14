import mock

from chroma_agent.lib.pacemaker import PacemakerNode
from iml_common.test.command_capture_testcase import (
    CommandCaptureTestCase,
    CommandCaptureCommand,
)


cib_configured_result = """<cib epoch="99" num_updates="1" admin_epoch="0" validate-with="pacemaker-1.2" cib-last-written="Wed Feb 11 02:41:36 2015" update-origin="lotus-33vm15" update-client="cibadmin" crm_feature_set="3.0.7" have-quorum="1" dc-uuid="lotus-33vm16">
  <configuration>
    <crm_config>
      <cluster_property_set id="cib-bootstrap-options">
        <nvpair id="cib-bootstrap-options-dc-version" name="dc-version" value="1.1.10-14.el6_5.3-368c726"/>
        <nvpair id="cib-bootstrap-options-cluster-infrastructure" name="cluster-infrastructure" value="openais"/>
        <nvpair id="cib-bootstrap-options-expected-quorum-votes" name="expected-quorum-votes" value="2"/>
        <nvpair id="cib-bootstrap-options-no-quorum-policy" name="no-quorum-policy" value="ignore"/>
        <nvpair id="cib-bootstrap-options-symmetric-cluster" name="symmetric-cluster" value="true"/>
        <nvpair id="cib-bootstrap-options-stonith-enabled" name="stonith-enabled" value="true"/>
      </cluster_property_set>
      <cluster_property_set id="integrated_manager_for_lustre_configuration">
        <nvpair id="integrated_manager_for_lustre_configuration_configured_by" name="configured_by" value="lotus-33vm15"/>
      </cluster_property_set>
    </crm_config>
  </configuration>
</cib>"""


class FencingTestCase(CommandCaptureTestCase):
    def setUp(self):
        super(FencingTestCase, self).setUp()

        self.fake_node_hostname = "fake.host.domain"
        self.fake_node_uuid = "1234567890"
        self.fake_node_attributes = {}

        self.stdin_lines = None

        def fake_hostname():
            return self.fake_node_hostname

        patcher = mock.patch("socket.gethostname", fake_hostname)
        patcher.start()

        @property
        def nodes(obj):
            pacemaker_node = PacemakerNode(self.fake_node_hostname, self.fake_node_uuid)
            pacemaker_node.attributes = self.fake_node_attributes
            return [pacemaker_node]

        patcher = mock.patch("chroma_agent.lib.pacemaker.PacemakerConfig.nodes", nodes)
        patcher.start()

        import chroma_agent.fence_chroma

        real_stdin_to_args = chroma_agent.fence_chroma.stdin_to_args

        def stdin_to_args(**kwargs):
            return real_stdin_to_args(self.stdin_lines)

        patcher = mock.patch("chroma_agent.fence_chroma.stdin_to_args", stdin_to_args)
        patcher.start()

        # nose confuses things
        import sys

        sys.argv = ["fence_chroma"]

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)


class TestAgentConfiguration(FencingTestCase):
    def setUp(self):
        super(TestAgentConfiguration, self).setUp()
        from chroma_agent.action_plugins import manage_corosync

        self.add_command(("cibadmin", "--query", "--local"))

        self.fake_node_attributes = {
            "0_fence_agent": "fake_agent",
            "0_fence_login": "admin",
            "0_fence_password": "yourmom",
        }

        # Reset the corosync configured flags
        manage_corosync.pacemaker_configured = False

    def test_multi_agent_config(self):
        from chroma_agent.action_plugins.manage_pacemaker import configure_fencing

        agents = [
            {
                "agent": "fence_virsh",
                "ipaddr": "1.2.3.4",
                "ipport": "22",
                "login": "monkey",
                "password": "banana",
                "plug": "monkey_vm",
            },
            {
                "agent": "fence_apc",
                "ipaddr": "4.3.2.1",
                "ipport": "23",
                "login": "apc",
                "password": "apc",
                "plug": "1",
            },
        ]

        for field in ["agent", "password", "login"]:
            self.add_command(
                (
                    "crm_attribute",
                    "-D",
                    "-t",
                    "nodes",
                    "-U",
                    self.fake_node_hostname,
                    "-n",
                    "0_fence_%s" % field,
                )
            )

        for i, agent in enumerate(agents):
            for key in [
                "ipport",
                "plug",
                "ipaddr",
                "login",
                "password",
                "agent",
            ]:  # The fields are the order the comamnds should occur in
                self.add_command(
                    (
                        "crm_attribute",
                        "-t",
                        "nodes",
                        "-U",
                        self.fake_node_hostname,
                        "-n",
                        "%d_fence_%s" % (i, key),
                        "-v",
                        agent[key],
                    )
                )

        self.add_command(
            (
                "cibadmin",
                "--modify",
                "--allow-create",
                "-o",
                "crm_config",
                "-X",
                '<cluster_property_set id="cib-bootstrap-options">\n<nvpair id="cib-bootstrap-options-stonith-enabled" name="stonith-enabled" value="true"/>\n',
            )
        )

        configure_fencing(agents)

        # HYD-2104: Ensure that the N_fence_agent attribute was added last.
        self.assertRanAllCommandsInOrder()

    def test_node_standby(self):
        from chroma_agent.action_plugins.manage_pacemaker import set_node_standby

        self.add_command(
            (
                "crm_attribute",
                "-N",
                self.fake_node_hostname,
                "-n",
                "standby",
                "-v",
                "on",
                "--lifetime=forever",
            )
        )
        set_node_standby(self.fake_node_hostname)

        self.assertRanAllCommands()

    def test_node_online(self):
        from chroma_agent.action_plugins.manage_pacemaker import set_node_online

        self.add_command(
            (
                "crm_attribute",
                "-N",
                self.fake_node_hostname,
                "-n",
                "standby",
                "-v",
                "off",
                "--lifetime=forever",
            )
        )

        set_node_online(self.fake_node_hostname)

        self.assertRanAllCommands()


class TestFenceAgent(FencingTestCase):
    def setUp(self):
        super(TestFenceAgent, self).setUp()

        self.fake_node_attributes = {
            "0_fence_agent": "fence_apc",
            "0_fence_login": "admin",
            "0_fence_password": "yourmom",
            "0_fence_ipaddr": "1.2.3.4",
            "0_fence_plug": "1",
        }

        call_template = (
            "%(0_fence_agent)s -a %(0_fence_ipaddr)s -u 23 -l %(0_fence_login)s -p %(0_fence_password)s -n %(0_fence_plug)s"
            % self.fake_node_attributes
        )
        call_base = tuple(call_template.split())

        self.add_commands(
            CommandCaptureCommand(("cibadmin", "--query", "--local")),
            CommandCaptureCommand((call_base + ("-o", "off"))),
            CommandCaptureCommand((call_base + ("-o", "on"))),
        )

    def test_finding_fenceable_nodes(self):
        self.reset_command_capture()
        self.add_command(("cibadmin", "--query", "--local"))

        # Not strictly an agent test, but the tested method is used by
        # the agent to generate the -o list output.
        from chroma_agent.lib.pacemaker import PacemakerConfig

        p_cfg = PacemakerConfig()
        self.assertEqual(len(p_cfg.fenceable_nodes), 1)

        self.assertRanAllCommandsInOrder()

    def test_fence_agent_reboot(self):
        from chroma_agent.fence_chroma import main as agent_main

        # Normal use, stonithd feeds commands via stdin
        self.stdin_lines = [
            "nodename=%s" % self.fake_node_hostname,
            "action=reboot",
            "port=%s" % self.fake_node_hostname,
        ]
        agent_main()
        self.assertRanAllCommands()

        self.reset_command_capture_logs()

        # Command-line should work too
        agent_main(["-o", "reboot", "-n", self.fake_node_hostname])
        self.assertRanAllCommands()

    def test_fence_agent_on_off(self):
        from chroma_agent.fence_chroma import main as agent_main

        # These options aren't likely to be used for STONITH, but they
        # should still work for manual invocation.
        agent_main(["-o", "off", "-n", self.fake_node_hostname])
        agent_main(["-o", "on", "-n", self.fake_node_hostname])

        self.assertRanAllCommands()

    def test_standby_node_not_fenced(self):
        self.reset_command_capture()
        self.add_command(("cibadmin", "--query", "--local"))

        # a node in standby should not be fenced
        self.fake_node_attributes = self.fake_node_attributes.copy()
        self.fake_node_attributes["standby"] = "on"

        from chroma_agent.fence_chroma import main as agent_main

        agent_args = ("-o", "off", "-n", self.fake_node_hostname)
        agent_main(agent_args)

        self.assertRanAllCommandsInOrder()


class TestFenceAgentMonitor(FencingTestCase):
    def setUp(self):
        super(TestFenceAgentMonitor, self).setUp()

        self.fake_node_attributes = {
            "0_fence_agent": "fence_apc",
            "0_fence_login": "admin",
            "0_fence_password": "yourmom",
            "0_fence_ipaddr": "1.2.3.4",
            "0_fence_plug": "1",
        }

        call_template = (
            "%(0_fence_agent)s -a %(0_fence_ipaddr)s -u 23 -l %(0_fence_login)s -p %(0_fence_password)s -n %(0_fence_plug)s"
            % self.fake_node_attributes
        )
        call_base = tuple(call_template.split())

        self.add_commands(
            CommandCaptureCommand(("cibadmin", "--query", "--local")),
            CommandCaptureCommand((call_base + ("-o", "monitor"))),
        )

    def test_fence_agent_monitor(self):
        patcher = mock.patch("sys.exit")
        exit = patcher.start()

        # Kind of a silly test, but we just want to make sure that our
        # agent's monitor option doesn't barf.
        from chroma_agent.fence_chroma import main as agent_main

        agent_main(["-o", "monitor", "-n", self.fake_node_hostname])
        exit.assert_called_with(0)

        # Make sure running with args from stdin works...
        self.stdin_lines = ["nodename=%s" % self.fake_node_hostname, "action=monitor"]
        agent_main()
        exit.assert_called_with(0)

        # Apparently stonithd sometimes(?) uses option instead of action...
        self.stdin_lines = ["nodename=%s" % self.fake_node_hostname, "option=monitor"]
        agent_main()
        exit.assert_called_with(0)
