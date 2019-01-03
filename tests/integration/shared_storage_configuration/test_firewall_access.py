from testconfig import config

from tests.utils.remote_firewall_control import RemoteFirewallControl
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.remote_operations import RealRemoteOperations


class TestFirewall(ChromaIntegrationTestCase):
    GREP_NOTFOUND_RC = 1

    def setUp(self):
        super(TestFirewall, self).setUp()
        self.remote_operations = RealRemoteOperations(self)

    def test_manager(self):
        """ Test that the manager has the required selinux setting and firewall access rules installed"""
        chroma_manager = config["chroma_managers"][0]

        self.assertEqual(
            "Enforcing\n", self.remote_operations._ssh_address(chroma_manager["address"], "getenforce").stdout
        )

        # TODO: refactor reset_cluster/reset_chroma_manager_db so that previous
        # state can be cleaned up without initializing the DB
        # then we can do a before/after firewall state comparison where
        # before and after are before chroma-config setup and after it
        # XXX: this assumes there is only one manager
        iml_port_proto_filter = [(80, "tcp"), (443, "tcp")]

        if chroma_manager.get("ntp_server", "localhost") == "localhost":
            iml_port_proto_filter.append((123, "udp"))

        iml_rules = self._process_ip_rules(chroma_manager, iml_port_proto_filter)

        self.assertEqual(len(iml_rules), len(iml_port_proto_filter))

    def _process_ip_rules(self, server, port_proto_filter=None):
        """
        Retrieve matching rules or entire set from given server

        :param server: target server we wish to retrieve rules from
        :param port_proto_filter: optional list of port/proto pairs to look for
        :return: RemoteFirewallControl.rules list of matching active firewall rules
        """
        # process rules on remote firewall in current state
        firewall = RemoteFirewallControl.create(server["address"], self.remote_operations._ssh_address_no_check)
        firewall.process_rules()

        if port_proto_filter:
            # we want to match firewall rules stored in member list 'firewall.rules' with those supplied in
            # port/proto tuples list 'port_proto_filter'. We also want to match rules with proto == 'all' (iptables).
            rules = []
            for rule in firewall.rules:
                if (int(rule.port), rule.protocol) in port_proto_filter:
                    rules.append(rule)
                elif rule.protocol == "any" and int(rule.port) in [f[0] for f in port_proto_filter]:
                    rules.append(rule)
            return rules

        else:
            return firewall.rules

    def test_agent(self):
        """
        Test that when hosts are added and a filesytem is created, that all required firewall accesses are
        installed
        """
        servers = self.TEST_SERVERS[0:4]

        host_addresses = [s["address"] for s in servers]
        self.hosts = self.add_hosts(host_addresses)
        self.configure_power_control(host_addresses)

        volumes = self.wait_for_shared_volumes(4, 4)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost1_volume = volumes[2]
        ost2_volume = volumes[3]
        self.set_volume_mounts(mgt_volume, self.hosts[0]["id"], self.hosts[1]["id"])
        self.set_volume_mounts(mdt_volume, self.hosts[1]["id"], self.hosts[0]["id"])
        self.set_volume_mounts(ost1_volume, self.hosts[2]["id"], self.hosts[3]["id"])
        self.set_volume_mounts(ost2_volume, self.hosts[3]["id"], self.hosts[2]["id"])

        self.filesystem_id = self.create_filesystem(
            self.hosts,
            {
                "name": "testfs",
                "mgt": {"volume_id": mgt_volume["id"]},
                "mdts": [{"volume_id": mdt_volume["id"], "conf_params": {}}],
                "osts": [
                    {"volume_id": ost1_volume["id"], "conf_params": {}},
                    {"volume_id": ost2_volume["id"], "conf_params": {}},
                ],
                "conf_params": {},
            },
        )

        mcast_ports = {}

        for server in servers:
            self.assertNotEqual(
                "Enforcing\n", self.remote_operations._ssh_address(server["address"], "getenforce").stdout
            )

            mcast_port = self.remote_operations.get_corosync_port(server["fqdn"])
            self.assertIsNotNone(mcast_port)

            mcast_ports[server["address"]] = mcast_port

            matching_rules = self._process_ip_rules(server, [(mcast_port, "udp"), (988, "tcp")])

            self.assertEqual(len(matching_rules), 2)

        # tear it down and make sure firewall rules are cleaned up
        self.graceful_teardown(self.chroma_manager)

        for server in servers:
            mcast_port = mcast_ports[server["address"]]

            matching_rules = self._process_ip_rules(server, [(mcast_port, "udp")])

            self.assertEqual(len(matching_rules), 0)

            # retrieve command string compatible with this server target
            firewall = RemoteFirewallControl.create(server["address"], self.remote_operations._ssh_address_no_check)

            # test that the remote firewall configuration doesn't include rules to enable the mcast_port
            self.remote_operations._ssh_address(
                server["address"],
                firewall.remote_validate_persistent_rule_cmd(mcast_port),
                expected_return_code=self.GREP_NOTFOUND_RC,
            )
