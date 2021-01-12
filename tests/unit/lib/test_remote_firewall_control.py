import unittest
import mock

from tests.utils.remote_firewall_control import RemoteFirewallControl
from tests.utils.remote_firewall_control import RemoteFirewallControlIpTables
from tests.utils.remote_firewall_control import RemoteFirewallControlFirewallCmd
from tests.unit.remote_operations import RealRemoteOperations as RRO
from emf_common.lib.shell import Shell


class TestRemoteFirewallControlIpTables(unittest.TestCase):
    """ Class for testing the RemoteFirewallControlIpTables classes """

    @staticmethod
    def example_func_1(address, command, expected_return_code=None):
        # example output from 'iptables -L' or 'service iptables status' if firewall not configured
        not_configured_output = """Table: filter
Chain INPUT (policy ACCEPT)
num  target     prot opt source               destination

Chain FORWARD (policy ACCEPT)
num  target     prot opt source               destination

Chain OUTPUT (policy ACCEPT)
num  target     prot opt source               destination

"""
        return Shell.RunResult(0, not_configured_output, "", False)

    @staticmethod
    def example_func_2(address, command, expected_return_code=None):
        return Shell.RunResult(0, "", "", False)

    @staticmethod
    def example_func_3(address, command, expected_return_code=None):
        # example output from 'iptables -L' or 'service iptables status'
        chain_output = """Table: filter
Chain INPUT (policy ACCEPT)
num  target     prot opt source               destination
1    ACCEPT     all  --  0.0.0.0/0            0.0.0.0/0           state RELATED,ESTABLISHED
2    ACCEPT     icmp --  0.0.0.0/0            0.0.0.0/0
3    ACCEPT     all  --  0.0.0.0/0            0.0.0.0/0
4    ACCEPT     udp  --  0.0.0.0/0            0.0.0.0/0           state NEW udp dpt:123
5    ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0           state NEW tcp dpt:22
6    ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0           state NEW tcp dpt:80
7    ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0           state NEW tcp dpt:443
8    REJECT     all  --  0.0.0.0/0            0.0.0.0/0           reject-with icmp-host-prohibited

Chain FORWARD (policy ACCEPT)
num  target     prot opt source               destination
1    REJECT     all  --  0.0.0.0/0            0.0.0.0/0           reject-with icmp-host-prohibited

Chain OUTPUT (policy ACCEPT)
num  target     prot opt source               destination

"""
        return Shell.RunResult(0, chain_output, "", False)

    def setUp(self):
        super(TestRemoteFirewallControlIpTables, self).setUp()

        self.test_firewall = RemoteFirewallControlIpTables("10.0.0.1", self.example_func_1)

        # reset controller_instances cls cache
        RemoteFirewallControl.controller_instances = {}

        self.mock_ssh = mock.patch("tests.unit.remote_operations.RealRemoteOperations._ssh_address").start()

    def tearDown(self):
        self.mock_ssh.stop()

    def test_create(self):
        values = {
            "which %s" % RemoteFirewallControlFirewallCmd.firewall_app_name: Shell.RunResult(1, "", "", False),
            "which %s" % RemoteFirewallControlIpTables.firewall_app_name: Shell.RunResult(0, "", "", False),
        }

        def side_effect(address, cmd):
            return values[cmd]

        self.mock_ssh.side_effect = side_effect

        new_controller = RemoteFirewallControl.create("0.0.0.0", RRO(None)._ssh_address)

        self.assertEquals(type(new_controller), RemoteFirewallControlIpTables)

    def test_remote_add_port(self):
        # should return a string representing remote command to add a port rule
        response = self.test_firewall.remote_add_port_cmd(123, "udp")

        self.assertEqual(response, "lokkit --port=123:udp --update")

    def test_remote_remove_port(self):
        # should return a string representing remote command to remove a port rule
        response = self.test_firewall.remote_remove_port_cmd(123, "udp")

        self.assertEqual(
            response, "iptables -D INPUT -m state --state new -p udp --dport 123 -j ACCEPT && iptables-save"
        )

    def test_remote_validate_persistent_rule(self):
        # should return a string representing remote command to validate a persistent port rule exists
        response = self.test_firewall.remote_validate_persistent_rule_cmd(123)

        self.assertEqual(
            response, 'grep -e "--dport 123\|--port=123" /etc/sysconfig/iptables /etc/sysconfig/system-config-firewall'
        )

    def test_process_rules_empty_ruleset(self):
        # firewall is active but with no matching rules
        self.test_firewall = RemoteFirewallControlIpTables("10.0.0.1", self.example_func_1)

        self.assertEqual(len(self.test_firewall.rules), 0)
        response = self.test_firewall.process_rules()

        self.assertEqual(response, None)
        self.assertEqual(len(self.test_firewall.rules), 0)

    def test_process_rules_incorrect(self):
        # incorrectly formatted string input is invalid and error string should be returned
        self.test_firewall = RemoteFirewallControlIpTables("10.0.0.1", self.example_func_2)

        self.assertEqual(len(self.test_firewall.rules), 0)
        try:
            self.test_firewall.process_rules()
            self.fail("incorrect command output was not detected!")
        except RuntimeError as e:
            self.assertEqual(
                str(e), 'process_rules(): "iptables -L INPUT -nv" command output contains unexpected iptables output'
            )
            pass

    def test_process_rules(self):
        # firewall is active and configured with matching rules
        self.test_firewall = RemoteFirewallControlIpTables("10.0.0.1", self.example_func_3)

        self.assertEqual(len(self.test_firewall.rules), 0)
        response = self.test_firewall.process_rules()

        # create example named tuple to compare with objects in rules list
        example_rule = RemoteFirewallControl.firewall_rule("80", "tcp")

        self.assertEqual(response, None)
        self.assertEqual(len(self.test_firewall.rules), 4)
        self.assertEqual(self.test_firewall.rules[2], example_rule)
        self.assertEqual(self.test_firewall.rules[2].port, example_rule.port)
        self.assertEqual(self.test_firewall.rules[2].protocol, example_rule.protocol)


class TestRemoteFirewallControlFirewallCmd(unittest.TestCase):
    """ Class for testing the RemoteFirewallControlFirewallCmd classes """

    @staticmethod
    def example_func_1(address, command, expected_return_code=None):
        return Shell.RunResult(0, "", "", False)

    @staticmethod
    def example_func_2(address, command, expected_return_code=None):
        return Shell.RunResult(0, "Chain INPUT (policy ACCEPT)", "", False)

    @staticmethod
    def example_func_3(address, command, expected_return_code=None):
        list_ports_output = """123/udp
22/tcp
80/tcp
443/tcp"""
        return Shell.RunResult(0, list_ports_output, "", False)

    @staticmethod
    def example_func_4(address, command, expected_return_code=None):
        list_ports_output = """123/udp 22/tcp 80/tcp 443/tcp
"""
        return Shell.RunResult(0, list_ports_output, "", False)

    def setUp(self):
        super(TestRemoteFirewallControlFirewallCmd, self).setUp()

        self.test_firewall = RemoteFirewallControlFirewallCmd("10.0.0.1", self.example_func_1)

        # reset controller_instances cls cache
        RemoteFirewallControl.controller_instances = {}

        self.mock_ssh = mock.patch("tests.unit.remote_operations.RealRemoteOperations._ssh_address").start()

    def tearDown(self):
        self.mock_ssh.stop()

    def test_create(self):
        values = {
            "which %s" % RemoteFirewallControlFirewallCmd.firewall_app_name: Shell.RunResult(0, "", "", False),
            "which %s" % RemoteFirewallControlIpTables.firewall_app_name: Shell.RunResult(1, "", "", False),
        }

        def side_effect(address, cmd):
            return values[cmd]

        self.mock_ssh.side_effect = side_effect

        new_controller = RemoteFirewallControl.create("0.0.0.0", RRO(None)._ssh_address)

        self.assertTrue(type(new_controller) == RemoteFirewallControlFirewallCmd)

    def test_create_both_present(self):
        values = {
            "which %s" % RemoteFirewallControlFirewallCmd.firewall_app_name: Shell.RunResult(0, "", "", False),
            "which %s" % RemoteFirewallControlIpTables.firewall_app_name: Shell.RunResult(0, "", "", False),
        }

        def side_effect(address, cmd):
            return values[cmd]

        self.mock_ssh.side_effect = side_effect

        new_controller = RemoteFirewallControl.create("0.0.0.0", RRO(None)._ssh_address)

        self.assertTrue(type(new_controller) == RemoteFirewallControlFirewallCmd)

    def test_create_neither_present(self):
        values = {
            "which %s" % RemoteFirewallControlFirewallCmd.firewall_app_name: Shell.RunResult(1, "", "", False),
            "which %s" % RemoteFirewallControlIpTables.firewall_app_name: Shell.RunResult(1, "", "", False),
        }

        def side_effect(address, cmd):
            return values[cmd]

        self.mock_ssh.side_effect = side_effect

        with self.assertRaises(RuntimeError):
            RemoteFirewallControl.create("0.0.0.0", RRO(None)._ssh_address)

    def test_remote_add_port(self):
        # should return a string representing remote command to add a port rule
        response = self.test_firewall.remote_add_port_cmd(123, "udp")

        self.assertEqual(response, 'for i in "" "--permanent"; do /usr/bin/firewall-cmd --add-port=123/udp $i; done')

    def test_remote_remove_port(self):
        # should return a string representing remote command to remove a port rule
        response = self.test_firewall.remote_remove_port_cmd(123, "udp")

        self.assertEqual(response, 'for i in "" "--permanent"; do /usr/bin/firewall-cmd --remove-port=123/udp $i; done')

    def test_remote_validate_persistent_rule(self):
        # should return a string representing remote command to validate a persistent port rule exists
        response = self.test_firewall.remote_validate_persistent_rule_cmd(123)

        self.assertEqual(response, "/usr/bin/firewall-cmd --list-ports --permanent | grep 123")

    def test_process_rules_empty_ruleset(self):
        # firewall is active but with no matching rules
        self.assertEqual(len(self.test_firewall.rules), 0)
        response = self.test_firewall.process_rules()

        self.assertEqual(response, None)
        self.assertEqual(len(self.test_firewall.rules), 0)

    def test_process_rules_incorrect(self):
        # incorrectly formatted string input is invalid and error string should be returned
        self.test_firewall = RemoteFirewallControlFirewallCmd("10.0.0.1", self.example_func_2)

        self.assertEqual(len(self.test_firewall.rules), 0)

        try:
            self.test_firewall.process_rules()
            self.fail("incorrect command output was not detected!")
        except RuntimeError as e:
            self.assertEqual(
                str(e),
                'process_rules(): "firewall-cmd --list-ports" command output contains unexpected '
                "firewall-cmd output",
            )
            pass

    def test_process_rules_format_1(self):
        # firewall is active and configured with matching rules
        self.test_firewall = RemoteFirewallControlFirewallCmd("10.0.0.1", self.example_func_3)

        self.assertEqual(len(self.test_firewall.rules), 0)
        response = self.test_firewall.process_rules()

        # create example named tuple to compare with objects in rules list
        example_rule = RemoteFirewallControl.firewall_rule("80", "tcp")

        self.assertEqual(response, None)
        self.assertEqual(len(self.test_firewall.rules), 4)
        self.assertEqual(self.test_firewall.rules[2], example_rule)
        self.assertEqual(self.test_firewall.rules[2].port, example_rule.port)
        self.assertEqual(self.test_firewall.rules[2].protocol, example_rule.protocol)

    def test_process_rules_format_2(self):
        # firewall is active and configured with matching rules
        self.test_firewall = RemoteFirewallControlFirewallCmd("10.0.0.1", self.example_func_4)

        self.assertEqual(len(self.test_firewall.rules), 0)
        response = self.test_firewall.process_rules()

        # create example named tuple to compare with objects in rules list
        example_rule = RemoteFirewallControl.firewall_rule("80", "tcp")

        self.assertEqual(response, None)
        self.assertEqual(len(self.test_firewall.rules), 4)
        self.assertEqual(self.test_firewall.rules[2], example_rule)
        self.assertEqual(self.test_firewall.rules[2].port, example_rule.port)
        self.assertEqual(self.test_firewall.rules[2].protocol, example_rule.protocol)
