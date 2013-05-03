import sys
import mock
from django.utils import unittest

from chroma_agent.action_plugins.manage_corosync import env, configure_corosync


class FakeEtherInfo(object):
    def __init__(self, attrs):
        self.__dict__.update(attrs)

    def __getattr__(self, attr):
        return self.__dict__[attr]


class fake_ethtool(object):
    def __init__(self, interfaces={}):
        self.interfaces = interfaces

    def get_interfaces_info(self, name):
        return [FakeEtherInfo(self.interfaces[name])]

    def get_devices(self):
        return self.interfaces.keys()

    def get_hwaddr(self, name):
        return self.interfaces[name]['mac_address']


class TestConfigureCorosync(unittest.TestCase):
    def setUp(self):
        super(TestConfigureCorosync, self).setUp()
        import chroma_agent.shell
        patcher = mock.patch.object(chroma_agent.shell, 'try_run')
        self.try_run = patcher.start()

        @classmethod
        def ring0(cls):
            return cls('eth0')
        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.CorosyncRingInterface.ring0', ring0)
        patcher.start()

        self.interfaces = {
                'eth0': {
                    'device': 'eth0',
                    'mac_address': 'de:ad:be:ef:ca:fe',
                    'ipv4_address': '192.168.1.1',
                    'ipv4_netmask': '255.255.255.0',
                    'has_link': True
                },
                'eth1': {
                    'device': 'eth1',
                    'mac_address': 'ba:db:ee:fb:aa:af',
                    'ipv4_address': None,
                    'ipv4_netmask': 0,
                    'has_link': True
                }
            }

        # Just mock out the entire module ... This will make the tests
        # run on OS X or on Linux without the python-ethtool package.
        self.old_ethtool = sys.modules.get("ethtool", None)
        ethtool = fake_ethtool(self.interfaces)
        sys.modules['ethtool'] = ethtool

        patcher = mock.patch('chroma_agent.node_admin.write_ifcfg')
        self.write_ifcfg = patcher.start()

        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync._render_config_file')
        self.render_config_file = patcher.start()
        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.unconfigure_pacemaker')
        patcher.start()

        from chroma_agent.action_plugins.manage_corosync import CorosyncRingInterface
        old_ring1 = CorosyncRingInterface.ring1

        @classmethod
        def ring1(cls, *args):
            self.interfaces['eth1']['ipv4_address'] = args[1]
            try:
                self.interfaces['eth1']['ipv4_netmask'] = args[2].prefixlen
            except AttributeError:
                self.interfaces['eth1']['ipv4_netmask'] = args[2]
            return old_ring1(*args)
        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.CorosyncRingInterface.ring1', ring1)
        patcher.start()

        old_set_address = CorosyncRingInterface.set_address

        def set_address(obj, address):
            if self.interfaces[obj.name]['ipv4_address'] is None:
                self.interfaces[obj.name]['ipv4_address'] = address.split("/")[0]
                self.interfaces[obj.name]['ipv4_netmask'] = address.split("/")[1]
            old_set_address(obj, address)
        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.CorosyncRingInterface.set_address', set_address)
        patcher.start()

        @property
        def has_link(obj):
            return self.interfaces[obj.name]['has_link']
        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.AutoDetectedInterface.has_link', has_link)
        patcher.start()

        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.AutoDetectedInterface.find_unused_port', return_value = "4242")
        patcher.start()

        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.AutoDetectedInterface.find_unused_port', return_value = 4242)
        patcher.start()

        patcher = mock.patch('chroma_agent.action_plugins.manage_corosync.AutoDetectedInterface.discover_existing_mcastport')
        patcher.start()

        self.conf_template = env.get_template('corosync.conf')

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        if self.old_ethtool:
            sys.modules['ethtool'] = self.old_ethtool

    def _render_test_config(self):
        from netaddr import IPNetwork
        interfaces = []
        for name in sorted(self.interfaces.keys()):
            interface = self.interfaces[name]
            bindnetaddr = IPNetwork("%s/%s" % (interface['ipv4_address'],
                                               interface['ipv4_netmask'])).network
            ringnumber = name[-1]
            interfaces.append(FakeEtherInfo({'ringnumber': ringnumber,
                                             'bindnetaddr': bindnetaddr,
                                             'mcastaddr': "226.94.%s.1" % ringnumber,
                                             'mcastport': 4242}))
        return self.conf_template.render(interfaces = interfaces)

    def test_manual_ring1_config(self):
        ring1_iface = "eth1"
        ring1_ipaddr = "10.42.42.42"
        ring1_netmask = "255.255.255.0"
        mcast_port = "4242"
        configure_corosync(ring1_iface, ring1_ipaddr, ring1_netmask, mcast_port)

        self.write_ifcfg.assert_called_with(ring1_iface, 'ba:db:ee:fb:aa:af', '10.42.42.42', '255.255.255.0')

        test_config = self._render_test_config()
        self.render_config_file.assert_called_with('/etc/corosync/corosync.conf', test_config)

    def test_semi_automatic_ring1_config(self):
        ring1_iface = "eth1"
        mcast_port = "4242"
        configure_corosync(ring1_iface = ring1_iface, mcast_port = mcast_port)

        self.write_ifcfg.assert_called_with(ring1_iface, 'ba:db:ee:fb:aa:af', '10.0.0.1', '255.255.255.0')

        test_config = self._render_test_config()
        self.render_config_file.assert_called_with('/etc/corosync/corosync.conf', test_config)

    def test_full_automatic_ring1_config(self):
        configure_corosync()

        self.write_ifcfg.assert_called_with('eth1', 'ba:db:ee:fb:aa:af', '10.0.0.1', '255.255.255.0')

        test_config = self._render_test_config()
        self.render_config_file.assert_called_with('/etc/corosync/corosync.conf', test_config)
