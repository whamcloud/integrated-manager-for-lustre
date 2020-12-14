from collections import namedtuple
import unittest
import mock
from chroma_agent.device_plugins.linux_network import (
    LinuxNetworkDevicePlugin,
    NetworkInterfaces,
)


class TestLinuxNetwork(unittest.TestCase):
    def mock_try_run(self, args):
        if args == ["ip", "addr"]:
            return """1: bond0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/ether 52:54:00:33:d9:15 brd ff:ff:ff:ff:ff:ff
    inet 192.168.10.79/21 brd 192.168.10.255 scope global bond0
    inet6 fe80::4e00:10ff:feac:61e0/64 scope link
       valid_lft forever preferred_lft forever
2: eth0.1.1?1b34*430: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/ether 52:54:00:33:a7:15 brd ff:ff:ff:ff:ff:ff
    inet 10.128.3.141/21 brd 10.128.7.255 scope global eth0.1.1?1b34*430
    inet6 fe80::4e00:10ff:feac:61e1/64 scope link
       valid_lft forever preferred_lft forever
3: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
4: eth2:  <BROADCAST,MULTICAST> mtu 1500 qdisc pfifo_fast state DOWN qlen 1000
    link/ether 52:54:00:33:a7:11 brd ff:ff:ff:ff:ff:ff
5: eth4: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/ether 52:54:00:33:a7:15 brd ff:ff:ff:ff:ff:ff
    inet 10.0.0.101/24 brd 10.0.0.255 scope global eth4
    inet6 fe80::200:ff:fe00:2/64 scope link
       valid_lft forever preferred_lft forever
6: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/infiniband 80:00:00:48:FE:80:00:00:00:00:00:00:00:00:00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff
    inet 192.168.4.23/23 brd 192.168.5.2555 scope global ib0
    inet6 fe80::225:90ff:ff1c:a229/64 scope link
       valid_lft forever preferred_lft forever"""
        elif args == ["lctl", "get_param", "-n", "nis"]:
            return "\n".join(
                [
                    "nid                      status alive refs peer  rtr   max    tx   min",
                    "0@lo                         up     0    3    0    0     0     0     0",
                    "192.168.10.79@tcp1001        up    -1    1    8    0   256   256   256",
                    "192.168.10.78@tcp1002        up    -1    1    8    0   256   256   256",
                    "10.0.0.101@tcp1              up    -1    1    8    0   256   256   256",
                    "192.168.4.23@o2ib99          up    -1    1    8    0   256   256   256",
                    "192.168.4.23@o2ib99          up    -1    1    8    0   256   256   256",
                    "192.168.4.23@o2ib99          up    -1    1    8    0   256   256   256",
                    "192.168.4.23@o2ib99          up    -1    1    8    0   256   256   256",
                    "192.168.4.23@o2ib99          up    -1    1    8    0   256   256   256",
                    "192.168.4.23@o2ib99          up    -1    1    8    0   256   256   256",
                ]
            )
        else:
            raise "Unknown args: " + repr(args)

    def test_network_interface(self):
        class mock_open:
            def __init__(self, fname):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exception_type, value, _traceback):
                pass

            def readlines(self):
                """
                The out of of a 'cat /proc/net/dev command.
                :return: Returns a list of lines as readlines would.
                """
                return [
                    "Inter-|   Receive                                                |  Transmit",
                    "face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed",
                    "lo: 8305400   85521    0    0    0     0          0         0  8305401   85521    0    0    0     0       0          0",
                    "bond0: 314203   2322    0    0    0     0          0         0  129834   82221    0    0    0     0       0          0",
                    "eth0.1.1?1b34*430: 318398818 20564    0    0    0     0          0         0  2069564   50037    0    0    0     0       0          0",
                    "eth4: 20400 6802    0    0    0     0          0         0  6859022   50337    0    0    0     0       0          0",
                    "ib0: 3286081 4756    0    0    0     0          0         0  4753096   50237    0    0    0     0       0          0",
                ]

        with mock.patch("__builtin__.open", mock_open):
            with mock.patch("chroma_agent.lib.shell.AgentShell.try_run", self.mock_try_run):
                interfaces = NetworkInterfaces()

        ResultCheck = namedtuple(
            "ResultCheck",
            [
                "interface",
                "mac_address",
                "type",
                "inet4_addr",
                "inet4_prefix",
                "inet6_addr",
                "rx_bytes",
                "tx_bytes",
                "up",
                "slave",
            ],
        )

        self.assertEqual(len(interfaces), 5)

        for result_check in [
            ResultCheck(
                "bond0",
                "52:54:00:33:d9:15",
                "tcp",
                "192.168.10.79",
                21,
                "fe80::4e00:10ff:feac:61e0",
                "314203",
                "129834",
                True,
                False,
            ),
            ResultCheck("eth2", "52:54:00:33:a7:11", "tcp", "", 0, "", "0", "0", False, False),
            ResultCheck(
                "eth4",
                "52:54:00:33:a7:15",
                "tcp",
                "10.0.0.101",
                24,
                "fe80::200:ff:fe00:2",
                "20400",
                "6859022",
                True,
                False,
            ),
            ResultCheck(
                "ib0",
                "80:00:00:48:FE:80:00:00:00:00:00:00:00:00:00:00:00:00:00:00",
                "o2ib",
                "192.168.4.23",
                23,
                "fe80::225:90ff:ff1c:a229",
                "3286081",
                "4753096",
                True,
                False,
            ),
        ]:

            interface = interfaces[result_check.interface]

            self.assertEqual(interface["mac_address"], result_check.mac_address)
            self.assertEqual(interface["type"], result_check.type)
            self.assertEqual(interface["inet4_address"], result_check.inet4_addr)
            self.assertEqual(interface["inet4_prefix"], result_check.inet4_prefix)
            self.assertEqual(interface["inet6_address"], result_check.inet6_addr)
            self.assertEqual(interface["rx_bytes"], result_check.rx_bytes)
            self.assertEqual(interface["tx_bytes"], result_check.tx_bytes)
            self.assertEqual(interface["up"], result_check.up)
            self.assertEqual(interface["slave"], result_check.slave)

        return interfaces

    def test_lnet_interface(self):
        with mock.patch("chroma_agent.lib.shell.AgentShell.try_run", self.mock_try_run):
            device_plugin = LinuxNetworkDevicePlugin(None)
            interfaces = self.test_network_interface()
            lnet_devices = device_plugin._lnet_devices(interfaces)

        ResultCheck = namedtuple(
            "ResultCheck",
            [
                "name",
                "lnd_address",
                "lnd_network",
                "lnd_type",
                "status",
                "alive",
                "refs",
                "peer",
                "rtr",
                "max",
                "tx",
                "min",
                "present",
            ],
        )

        self.assertEqual(len(lnet_devices), 3)

        for result_check in [
            ResultCheck("lo", "0", "0", "tcp", "up", "0", "3", "0", "0", "0", "0", "0", False),
            ResultCheck(
                "bond0",
                "192.168.10.79",
                "1001",
                "tcp",
                "up",
                "-1",
                "1",
                "8",
                "0",
                "256",
                "256",
                "256",
                True,
            ),
            ResultCheck(
                "fake",
                "192.168.10.78",
                "1002",
                "tcp",
                "up",
                "-1",
                "1",
                "8",
                "0",
                "256",
                "256",
                "256",
                False,
            ),
            ResultCheck(
                "eth4",
                "10.0.0.101",
                "1",
                "tcp",
                "up",
                "-1",
                "1",
                "8",
                "0",
                "256",
                "256",
                "256",
                True,
            ),
            ResultCheck(
                "ib0",
                "192.168.4.23",
                "99",
                "o2ib",
                "up",
                "-1",
                "1",
                "8",
                "0",
                "256",
                "256",
                "256",
                True,
            ),
        ]:
            try:
                nid = lnet_devices[result_check.name]
            except KeyError:
                self.assertEqual(result_check.present, False)
                continue

            self.assertEqual(nid["nid_address"], result_check.lnd_address)
            self.assertEqual(nid["lnd_network"], result_check.lnd_network)
            self.assertEqual(nid["lnd_type"], result_check.lnd_type)
