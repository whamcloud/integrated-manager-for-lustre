from collections import namedtuple
from django.utils import unittest
import mock
from chroma_agent.device_plugins.linux_network import LinuxNetworkDevicePlugin


class TestLinuxNetwork(unittest.TestCase):
    def test_network_interface(self):
        def mock_try_run_ifconfig(args):
            return """bond0         Link encap:Ethernet  HWaddr 4C:00:10:AC:61:E0
        inet addr:192.168.10.79  Bcast:192.168.10.255 \        Mask:255.255.255.0
        inet6 addr: fe80::4e00:10ff:feac:61e0/64 Scope:Link
        UP BROADCAST RUNNING MASTER MULTICAST  MTU:1500 Metric:1
        RX packets:3091 errors:0 dropped:0 overruns:0 frame:0
        TX packets:880 errors:0 dropped:0 overruns:0 carrier:0
        collisions:0 txqueuelen:0
        RX bytes:314203 (306.8 KiB)  TX bytes:129834 (126.7 KiB)

eth0    Link encap:Ethernet  HWaddr 4C:00:10:AC:61:E1
        inet6 addr: fe80::4e00:10ff:feac:61e1/64 Scope:Link
        UP BROADCAST RUNNING SLAVE MULTICAST  MTU:1500 Metric:1
        RX packets:1581 errors:0 dropped:0 overruns:0 frame:0
        TX packets:448 errors:0 dropped:0 overruns:0 carrier:0
        collisions:0 txqueuelen:1000
        RX bytes:162084 (158.2 KiB)  TX bytes:67245 (65.6 KiB)
        Interrupt:193 Base address:0x8c00

eth1    Link encap:Ethernet  HWaddr 4C:00:10:AC:61:E2
        inet6 addr: fe80::4e00:10ff:feac:61e2/64 Scope:Link
        UP BROADCAST RUNNING SLAVE MULTICAST  MTU:1500 Metric:1
        RX packets:1513 errors:0 dropped:0 overruns:0 frame:0
        TX packets:444 errors:0 dropped:0 overruns:0 carrier:0
        collisions:0 txqueuelen:1000
        RX bytes:152299 (148.7 KiB)  TX bytes:64517 (63.0 KiB)
        Interrupt:185 Base address:0x6000

lo      Link encap:Local Loopback
        inet addr:127.0.0.1  Mask:255.0.0.0
        inet6 addr: ::1/128 Scope:Host
        UP LOOPBACK RUNNING  MTU:16436  Metric:1
        RX packets:39959872 errors:0 dropped:0 overruns:0 frame:0
        TX packets:39959872 errors:0 dropped:0 overruns:0 carrier:0
        collisions:0 txqueuelen:0
        RX bytes:11955542777 (11.9 GB)  TX bytes:11955542777 (11.9 GB)

eth2    Link encap:Ethernet  HWaddr 00:02:c9:0e:38:2c
        BROADCAST MULTICAST  MTU:1500  Metric:1
        RX packets:0 errors:0 dropped:0 overruns:0 frame:0
        TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
        collisions:0 txqueuelen:1000
        RX bytes:0 (0.0 B)  TX bytes:0 (0.0 B)

eth4    Link encap:Ethernet  HWaddr 00:00:00:00:00:02
        inet addr:10.0.0.101  Bcast:10.0.0.255  Mask:255.255.255.0
        inet6 addr: fe80::200:ff:fe00:2/64 Scope:Link
        UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
        RX packets:347 errors:0 dropped:0 overruns:0 frame:0
        TX packets:55864 errors:0 dropped:0 overruns:0 carrier:0
        collisions:0 txqueuelen:1000
        RX bytes:20400 (19.9 KiB)  TX bytes:6859022 (6.5 MiB)
        Interrupt:11

ib0     Link encap:InfiniBand  HWaddr 80:00:00:48:FE:80:00:00:00:00:00:00:00:00:00:00:00:00:00:00
        inet addr:192.168.4.23  Bcast:192.168.5.255  Mask:255.255.254.0
        inet6 addr: fe80::225:90ff:ff1c:a229/64 Scope:Link
        UP BROADCAST RUNNING MULTICAST  MTU:2044  Metric:1
        RX packets:55810 errors:0 dropped:0 overruns:0 frame:0
        TX packets:47276 errors:0 dropped:0 overruns:0 carrier:0
        collisions:0 txqueuelen:256
        RX bytes:3286081 (3.1 MiB)  TX bytes:4753096 (4.5 MiB)"""

        with mock.patch('chroma_agent.shell.try_run', mock_try_run_ifconfig):
            device_plugin = LinuxNetworkDevicePlugin(None)
            interfaces = device_plugin._ifconfig()

        ResultCheck = namedtuple("ResultCheck",
                                 ["interface", "mac_address", "type", "inet4_addr", "inet6_addr",
                                 "rx_bytes", "tx_bytes", "up", "slave"])

        self.assertEqual(len(interfaces), 4)

        for result_check in [ResultCheck("bond0", "4C:00:10:AC:61:E0", "tcp", "192.168.10.79", "fe80::4e00:10ff:feac:61e0/64", "314203", "129834", True, False),
                             ResultCheck("eth2", "00:02:c9:0e:38:2c", "tcp", "", "", "0", "0", False, False),
                             ResultCheck("eth4", "00:00:00:00:00:02", "tcp", "10.0.0.101", "fe80::200:ff:fe00:2/64", "20400", "6859022", True, False),
                             ResultCheck("ib0", "80:00:00:48:FE:80:00:00:00:00:00:00:00:00:00:00:00:00:00:00",
                                         "o2ib", "192.168.4.23", "fe80::225:90ff:ff1c:a229/64", "3286081", "4753096", True, False)]:

            interface = interfaces[result_check.interface]

            self.assertEqual(interface['mac_address'], result_check.mac_address)
            self.assertEqual(interface['type'], result_check.type)
            self.assertEqual(interface['inet4_address'], result_check.inet4_addr)
            self.assertEqual(interface['inet6_address'], result_check.inet6_addr)
            self.assertEqual(interface['rx_bytes'], result_check.rx_bytes)
            self.assertEqual(interface['tx_bytes'], result_check.tx_bytes)
            self.assertEqual(interface['up'], result_check.up)
            self.assertEqual(interface['slave'], result_check.slave)

        return interfaces

    def test_lnet_interface(self):
        class mock_open:
            def __init__(self, fname):
                pass

            def readlines(self):
                return ["nid                      status alive refs peer  rtr   max    tx   min",
                        "0@lo                         up     0    3    0    0     0     0     0",
                        "192.168.10.79@tcp1001        up    -1    1    8    0   256   256   256",
                        "192.168.10.78@tcp1002        up    -1    1    8    0   256   256   256",
                        "10.0.0.101@tcp1              up    -1    1    8    0   256   256   256",
                        "192.168.4.23@tcp99           up    -1    1    8    0   256   256   256"]

        with mock.patch('__builtin__.open', mock_open):
                device_plugin = LinuxNetworkDevicePlugin(None)
                interfaces = self.test_network_interface()
                lnet_devices = device_plugin._lnet_devices(interfaces)

        ResultCheck = namedtuple("ResultCheck",
                                 ["name", "lnd_address", "lnd_network", "lnd_type", "status", "alive", "refs", "peer", "rtr", "max", "tx", "min", "present"])

        self.assertEqual(len(lnet_devices), 3)

        for result_check in [ResultCheck("lo",    "0",             "0",    "tcp", "up", "0",  "3", "0", "0",  "0",  "0",    "0",  False),
                             ResultCheck("bond0", "192.168.10.79", "1001", "tcp", "up", "-1", "1", "8", "0", "256", "256", "256", True),
                             ResultCheck("fake",  "192.168.10.78", "1002", "tcp", "up", "-1", "1", "8", "0", "256", "256", "256", False),
                             ResultCheck("eth4",  "10.0.0.101",    "1",    "tcp", "up", "-1", "1", "8", "0", "256", "256", "256", True),
                             ResultCheck("ib0",   "192.168.4.23",  "99",   "tcp", "up", "-1", "1", "8", "0", "256", "256", "256", True)]:
            try:
                nid = lnet_devices[result_check.name]
            except KeyError:
                self.assertEqual(result_check.present, False)
                continue

            self.assertEqual(nid['nid_address'], result_check.lnd_address)
            self.assertEqual(nid['lnd_network'], result_check.lnd_network)
            self.assertEqual(nid['lnd_type'], result_check.lnd_type)
            self.assertEqual(nid['status'], result_check.status)
            self.assertEqual(nid['alive'], result_check.alive)
            self.assertEqual(nid['refs'], result_check.refs)
            self.assertEqual(nid['peer'], result_check.peer)
            self.assertEqual(nid['rtr'], result_check.rtr)
            self.assertEqual(nid['max'], result_check.max)
            self.assertEqual(nid['tx'], result_check.tx)
            self.assertEqual(nid['min'], result_check.min)



#ResultCheck = namedtuple("ResultCheck",
#                         ["interface", "mac_address", "type", "inet4_addr", "inet6_addr",
#                         "rx_bytes", "tx_bytes", "up", "slave"])
#
#self.assertEqual(len(interfaces), 3)
#
#for result_check in [ResultCheck("bond0", "4C:00:10:AC:61:E0", "tcp", "192.168.10.79", "fe80::4e00:10ff:feac:61e0/64", "314203", "129834", True, False),
#                     ResultCheck("eth2", "00:02:c9:0e:38:2c", "tcp", '', '', "0", "0", False, False),
#                     ResultCheck("ib0", "80:00:00:48:FE:80:00:00:00:00:00:00:00:00:00:00:00:00:00:00",
#                                 "o2ib", "192.168.4.23", "fe80::225:90ff:ff1c:a229/64", "3286081", "4753096", True, False)]:
#
#    interface = interfaces[result_check.interface]
#
#    self.assertEqual(interface['mac_address'], result_check.mac_address)
#    self.assertEqual(interface['type'], result_check.type)
#    self.assertEqual(interface['inet4_address'], result_check.inet4_addr)
#    self.assertEqual(interface['inet6_address'], result_check.inet6_addr)
#    self.assertEqual(interface['rx_bytes'], result_check.rx_bytes)
#    self.assertEqual(interface['tx_bytes'], result_check.tx_bytes)
#    self.assertEqual(interface['up'], result_check.up)
#    self.assertEqual(interface['slave'], result_check.slave)
#
#return interfaces
