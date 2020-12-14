import mock

import unittest

from chroma_agent.action_plugins.manage_network import open_firewall, close_firewall


class TestManageNetworking(unittest.TestCase):
    @mock.patch("iml_common.lib.firewall_control.FirewallControl.create")
    def test_open_firewall_port(self, mock_firewall_control):
        open_firewall(1, 2, "bob", "uncle", False)
        open_firewall(3, 4, "sid", "vicious", True)

        mock_firewall_control.assert_has_calls(mock.call(1, "bob", "uncle", False, 2))
        mock_firewall_control.assert_has_calls(mock.call(3, "sid", "vicious", True, 4))

    @mock.patch("iml_common.lib.firewall_control.FirewallControl.create")
    def test_close_firewall_port(self, mock_firewall_control):
        close_firewall(1, 2, "bob", "uncle", False)
        close_firewall(3, 4, "sid", "vicious", True)

        mock_firewall_control.assert_has_calls(mock.call(1, "bob", "uncle", False, 2))
        mock_firewall_control.assert_has_calls(mock.call(3, "sid", "vicious", True, 4))
