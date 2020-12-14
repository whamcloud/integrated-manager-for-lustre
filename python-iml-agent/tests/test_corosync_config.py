import sys
import mock

from iml_common.test.command_capture_testcase import (
    CommandCaptureTestCase,
    CommandCaptureCommand,
)
from iml_common.lib.firewall_control import FirewallControlEL7
from iml_common.lib.service_control import ServiceControlEL7
from iml_common.lib.agent_rpc import agent_result_ok


class FakeEtherInfo(object):
    def __init__(self, attrs):
        self.__dict__.update(attrs)

    def __getattr__(self, attr):
        return self.__dict__[attr]


class fake_ethtool(object):
    IFF_SLAVE = 2048

    def __init__(self, interfaces={}):
        self.interfaces = interfaces

    def get_interfaces_info(self, name):
        return [FakeEtherInfo(self.interfaces[name])]

    def get_devices(self):
        return self.interfaces.keys()

    def get_hwaddr(self, name):
        return self.interfaces[name]["mac_address"]

    def get_flags(self, name):
        # just hard-code this for now
        return 4163


class TestConfigureCorosync(CommandCaptureTestCase):
    def setUp(self):
        super(TestConfigureCorosync, self).setUp()

        from chroma_agent.lib.corosync import CorosyncRingInterface
        from chroma_agent.lib.corosync import env

        def get_shared_ring():
            return CorosyncRingInterface("eth0.1.1?1b34*430")

        mock.patch("chroma_agent.lib.corosync.get_shared_ring", get_shared_ring).start()

        self.interfaces = {
            "eth0.1.1?1b34*430": {
                "device": "eth0.1.1?1b34*430",
                "mac_address": "de:ad:be:ef:ca:fe",
                "ipv4_address": "192.168.1.1",
                "ipv4_netmask": "255.255.255.0",
                "link_up": True,
            },
            "eth1": {
                "device": "eth1",
                "mac_address": "ba:db:ee:fb:aa:af",
                "ipv4_address": None,
                "ipv4_netmask": 0,
                "link_up": True,
            },
        }

        # Just mock out the entire module ... This will make the tests
        # run on OS X or on Linux without the python-ethtool package.
        self.old_ethtool = sys.modules.get("ethtool", None)
        ethtool = fake_ethtool(self.interfaces)
        sys.modules["ethtool"] = ethtool

        self.write_ifcfg = mock.patch("chroma_agent.lib.node_admin.write_ifcfg").start()
        self.unmanage_network = mock.patch("chroma_agent.lib.node_admin.unmanage_network").start()

        self.write_config_to_file = mock.patch(
            "chroma_agent.action_plugins.manage_corosync.write_config_to_file"
        ).start()

        mock.patch("chroma_agent.action_plugins.manage_pacemaker.unconfigure_pacemaker").start()

        old_set_address = CorosyncRingInterface.set_address

        def set_address(obj, address, prefix):
            if self.interfaces[obj.name]["ipv4_address"] is None:
                self.interfaces[obj.name]["ipv4_address"] = address
                self.interfaces[obj.name]["ipv4_netmask"] = prefix
            old_set_address(obj, address, prefix)

        mock.patch("chroma_agent.lib.corosync.CorosyncRingInterface.set_address", set_address).start()

        @property
        def has_link(obj):
            return self.interfaces[obj.name]["link_up"]

        self.link_patcher = mock.patch("chroma_agent.lib.corosync.CorosyncRingInterface.has_link", has_link)
        self.link_patcher.start()

        mock.patch("chroma_agent.lib.corosync.find_unused_port", return_value=4242).start()

        mock.patch("chroma_agent.lib.corosync.discover_existing_mcastport").start()

        self.conf_template = env.get_template("corosync.conf")

        # mock out firewall control calls and check with assert_has_calls in tests
        self.mock_add_port = mock.patch.object(FirewallControlEL7, "_add_port", return_value=None).start()
        self.mock_remove_port = mock.patch.object(FirewallControlEL7, "_remove_port", return_value=None).start()

        # mock out service control objects with ServiceControlEL7 spec and check with assert_has_calls in tests
        # this assumes, quite rightly, that manage_corosync and manage_corosync2 will not both be used in the same test
        self.mock_corosync_service = mock.create_autospec(ServiceControlEL7)
        self.mock_corosync_service.enable.return_value = None
        self.mock_corosync_service.disable.return_value = None
        mock.patch(
            "chroma_agent.action_plugins.manage_corosync.corosync_service",
            self.mock_corosync_service,
        ).start()
        mock.patch(
            "chroma_agent.action_plugins.manage_corosync2.corosync_service",
            self.mock_corosync_service,
        ).start()

        self.mock_pcsd_service = mock.create_autospec(ServiceControlEL7)
        self.mock_pcsd_service.enable.return_value = None
        self.mock_pcsd_service.start.return_value = None
        mock.patch(
            "chroma_agent.action_plugins.manage_corosync2.pcsd_service",
            self.mock_pcsd_service,
        ).start()

        mock.patch(
            "chroma_agent.action_plugins.manage_corosync.firewall_control",
            FirewallControlEL7(),
        ).start()
        mock.patch(
            "chroma_agent.action_plugins.manage_corosync2.firewall_control",
            FirewallControlEL7(),
        ).start()

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        if self.old_ethtool:
            sys.modules["ethtool"] = self.old_ethtool

    def _ring_iface_info(self, mcast_port):
        from netaddr import IPNetwork

        interfaces = []
        for name in sorted(self.interfaces.keys()):
            interface = self.interfaces[name]
            bindnetaddr = IPNetwork("%s/%s" % (interface["ipv4_address"], interface["ipv4_netmask"])).network
            ringnumber = name[-1]
            interfaces.append(
                FakeEtherInfo(
                    {
                        "ringnumber": ringnumber,
                        "bindnetaddr": bindnetaddr,
                        "mcastaddr": "226.94.%s.1" % ringnumber,
                        "mcastport": mcast_port,
                    }
                )
            )
        return interfaces

    def _render_test_config(self, mcast_port):
        return self.conf_template.render(interfaces=self._ring_iface_info(mcast_port))

    def test_manual_ring1_config(self):
        from chroma_agent.action_plugins.manage_corosync_common import configure_network
        from chroma_agent.action_plugins.manage_corosync import configure_corosync

        ring0_name = "eth0.1.1?1b34*430"
        ring1_name = "eth1"
        ring1_ipaddr = "10.42.42.42"
        ring1_netmask = "255.255.255.0"
        old_mcast_port = None
        new_mcast_port = "4242"

        # add shell commands to be expected
        self.add_commands(
            CommandCaptureCommand(("/sbin/ip", "link", "set", "dev", ring1_name, "up")),
            CommandCaptureCommand(
                (
                    "/sbin/ip",
                    "addr",
                    "add",
                    "%s/%s" % (ring1_ipaddr, ring1_netmask),
                    "dev",
                    ring1_name,
                )
            ),
        )

        # now a two-step process! first network...
        self.assertEqual(
            agent_result_ok,
            configure_network(
                ring0_name,
                ring1_name=ring1_name,
                ring1_ipaddr=ring1_ipaddr,
                ring1_prefix=ring1_netmask,
            ),
        )

        self.write_ifcfg.assert_called_with(ring1_name, "ba:db:ee:fb:aa:af", "10.42.42.42", "255.255.255.0")
        self.unmanage_network.assert_called_with(ring1_name, "ba:db:ee:fb:aa:af")

        # ...then corosync
        self.assertEqual(
            agent_result_ok,
            configure_corosync(ring0_name, ring1_name, old_mcast_port, new_mcast_port),
        )

        test_config = self._render_test_config(new_mcast_port)
        self.write_config_to_file.assert_called_with("/etc/corosync/corosync.conf", test_config)

        # check correct firewall and service calls were made
        self.mock_add_port.assert_has_calls([mock.call(new_mcast_port, "udp")])
        self.mock_remove_port.assert_not_called()
        self.mock_corosync_service.enable.assert_called_once_with()

        self.assertRanAllCommandsInOrder()

        self.mock_remove_port.reset_mock()
        self.mock_add_port.reset_mock()
        self.mock_corosync_service.reset_mock()

        # ...now change corosync mcast port
        old_mcast_port = "4242"
        new_mcast_port = "4246"

        self.assertEqual(
            agent_result_ok,
            configure_corosync(ring0_name, ring1_name, old_mcast_port, new_mcast_port),
        )

        test_config = self._render_test_config(new_mcast_port)
        # check we try to write template with new_mcast_port value
        self.write_config_to_file.assert_called_with("/etc/corosync/corosync.conf", test_config)

        # check correct firewall and service calls were made
        self.mock_remove_port.assert_has_calls([mock.call(old_mcast_port, "udp")])
        self.mock_add_port.assert_has_calls([mock.call(new_mcast_port, "udp")])
        self.mock_corosync_service.enable.assert_called_once_with()

    def _test_manual_ring1_config_corosync2(self, fqdn=False):
        import socket
        from chroma_agent.action_plugins.manage_corosync2 import (
            configure_corosync2_stage_1,
        )
        from chroma_agent.action_plugins.manage_corosync2 import (
            configure_corosync2_stage_2,
        )
        from chroma_agent.action_plugins.manage_corosync2 import PCS_TCP_PORT
        from chroma_agent.action_plugins.manage_corosync_common import configure_network

        ring0_name = "eth0.1.1?1b34*430"
        ring1_name = "eth1"
        ring1_ipaddr = "10.42.42.42"
        ring1_netmask = "255.255.255.0"
        mcast_port = "4242"
        new_node_fqdn = "servera.somewhere.org"
        pcs_password = "bondJAMESbond"

        # add shell commands to be expected
        self.add_commands(
            CommandCaptureCommand(("/sbin/ip", "link", "set", "dev", ring1_name, "up")),
            CommandCaptureCommand(
                (
                    "/sbin/ip",
                    "addr",
                    "add",
                    "/".join([ring1_ipaddr, ring1_netmask]),
                    "dev",
                    ring1_name,
                )
            ),
        )
        if fqdn:
            self.add_commands(CommandCaptureCommand(("hostnamectl", "set-hostname", new_node_fqdn)))

        self.add_commands(
            CommandCaptureCommand(("bash", "-c", "echo bondJAMESbond | passwd --stdin hacluster")),
            CommandCaptureCommand(
                tuple(["pcs", "cluster", "auth"] + [new_node_fqdn] + ["-u", "hacluster", "-p", "bondJAMESbond"])
            ),
        )

        # now a two-step process! first network...
        self.assertEqual(
            agent_result_ok,
            configure_network(
                ring0_name,
                ring1_name=ring1_name,
                ring1_ipaddr=ring1_ipaddr,
                ring1_prefix=ring1_netmask,
            ),
        )

        self.write_ifcfg.assert_called_with(ring1_name, "ba:db:ee:fb:aa:af", "10.42.42.42", "255.255.255.0")

        # fetch ring info
        r0, r1 = self._ring_iface_info(mcast_port)

        # add shell commands to be expected populated with ring interface info
        self.add_command(
            (
                "pcs",
                "cluster",
                "setup",
                "--name",
                "lustre-ha-cluster",
                "--force",
                new_node_fqdn,
                "--transport",
                "udp",
                "--rrpmode",
                "passive",
                "--addr0",
                str(r0.bindnetaddr),
                "--mcast0",
                str(r0.mcastaddr),
                "--mcastport0",
                str(r0.mcastport),
                "--addr1",
                str(r1.bindnetaddr),
                "--mcast1",
                str(r1.mcastaddr),
                "--mcastport1",
                str(r1.mcastport),
                "--token",
                "17000",
                "--fail_recv_const",
                "10",
            )
        )

        # ...then corosync / pcsd
        if fqdn:
            self.assertEqual(
                agent_result_ok,
                configure_corosync2_stage_1(mcast_port, pcs_password, new_node_fqdn),
            )
        else:
            self.assertEqual(agent_result_ok, configure_corosync2_stage_1(mcast_port, pcs_password))

        self.assertEqual(
            agent_result_ok,
            configure_corosync2_stage_2(ring0_name, ring1_name, new_node_fqdn, mcast_port, pcs_password, True),
        )

        # check correct firewall and service calls were made
        self.mock_add_port.assert_has_calls([mock.call(mcast_port, "udp"), mock.call(PCS_TCP_PORT, "tcp")])
        self.mock_remove_port.assert_not_called()
        self.mock_pcsd_service.start.assert_called_once_with()
        self.mock_corosync_service.enable.assert_called_once_with()
        self.mock_pcsd_service.enable.assert_called_once_with()

        self.mock_remove_port.reset_mock()
        self.mock_add_port.reset_mock()
        self.mock_corosync_service.reset_mock()

        self.assertRanAllCommandsInOrder()

    def test_manual_ring1_config_corosync2(self):
        self._test_manual_ring1_config_corosync2(False)

    def test_manual_ring1_config_corosync2_fqdn(self):
        self._test_manual_ring1_config_corosync2(True)

    def test_unconfigure_corosync2(self):
        from chroma_agent.action_plugins.manage_corosync2 import unconfigure_corosync2
        from chroma_agent.action_plugins.manage_corosync2 import PCS_TCP_PORT

        host_fqdn = "serverb.somewhere.org"
        mcast_port = "4242"

        # add shell commands to be expected
        self.add_commands(
            CommandCaptureCommand(("pcs", "status", "nodes", "corosync")),
            CommandCaptureCommand(("pcs", "--force", "cluster", "node", "remove", host_fqdn)),
        )

        self.assertEqual(agent_result_ok, unconfigure_corosync2(host_fqdn, mcast_port))

        self.mock_corosync_service.disable.assert_called_once_with()
        self.mock_remove_port.assert_has_calls([mock.call(PCS_TCP_PORT, "tcp"), mock.call(mcast_port, "udp")])

        self.assertRanAllCommandsInOrder()

    def test_find_subnet(self):
        from chroma_agent.lib.corosync import find_subnet
        from netaddr import IPNetwork

        test_map = {
            ("192.168.1.0", "24"): IPNetwork("10.0.0.0/24"),
            ("10.0.1.0", "24"): IPNetwork("10.128.0.0/24"),
            ("10.128.0.0", "9"): IPNetwork("10.0.0.0/9"),
            ("10.127.255.254", "9"): IPNetwork("10.128.0.0/9"),
            ("10.255.255.255", "32"): IPNetwork("10.0.0.0/32"),
        }

        for args, output in test_map.items():
            self.assertEqual(output, find_subnet(*args))

    def test_link_state_unknown(self):
        with mock.patch("__builtin__.open", mock.mock_open(read_data="unknown")):
            with mock.patch(
                "chroma_agent.lib.corosync.CorosyncRingInterface.__getattr__",
                return_value=False,
            ):
                with mock.patch("os.path.exists", return_value=True):
                    self.link_patcher.stop()

                    from chroma_agent.lib.corosync import get_shared_ring

                    iface = get_shared_ring()

                    # add shell commands to be expected
                    self.add_commands(
                        CommandCaptureCommand(("/sbin/ip", "link", "set", "dev", iface.name, "up")),
                        CommandCaptureCommand(("/sbin/ip", "link", "set", "dev", iface.name, "down")),
                    )

                    self.assertFalse(iface.has_link)

                    self.assertRanAllCommandsInOrder()
