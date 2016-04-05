import os
import shutil
import sys
import mock
import tempfile

from tests.command_capture_testcase import CommandCaptureTestCase
from tests.command_capture_testcase import CommandCaptureCommand
from chroma_agent.action_plugins.manage_corosync2 import configure_corosync2_stage_1
from chroma_agent.action_plugins.manage_corosync2 import configure_corosync2_stage_2
from chroma_agent.action_plugins.manage_corosync2 import unconfigure_corosync2
from chroma_agent.action_plugins.manage_corosync_common import configure_network
from chroma_agent.lib.corosync import env
from chroma_agent.action_plugins.manage_corosync import configure_corosync


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
        return self.interfaces[name]['mac_address']

    def get_flags(self, name):
        # just hard-code this for now
        return 4163


class TestConfigureCorosync(CommandCaptureTestCase):
    def setUp(self):
        super(TestConfigureCorosync, self).setUp()

        from chroma_agent.lib.corosync import CorosyncRingInterface

        def get_ring0():
            return CorosyncRingInterface('eth0.1.1?1b34*430')

        mock.patch('chroma_agent.lib.corosync.get_ring0', get_ring0).start()

        self.interfaces = {
                'eth0.1.1?1b34*430': {
                    'device': 'eth0.1.1?1b34*430',
                    'mac_address': 'de:ad:be:ef:ca:fe',
                    'ipv4_address': '192.168.1.1',
                    'ipv4_netmask': '255.255.255.0',
                    'link_up': True
                },
                'eth1': {
                    'device': 'eth1',
                    'mac_address': 'ba:db:ee:fb:aa:af',
                    'ipv4_address': None,
                    'ipv4_netmask': 0,
                    'link_up': True
                }
            }

        # Just mock out the entire module ... This will make the tests
        # run on OS X or on Linux without the python-ethtool package.
        self.old_ethtool = sys.modules.get("ethtool", None)
        ethtool = fake_ethtool(self.interfaces)
        sys.modules['ethtool'] = ethtool

        self.write_ifcfg = mock.patch('chroma_agent.node_admin.write_ifcfg').start()
        self.unmanage_network = mock.patch('chroma_agent.node_admin.unmanage_network').start()

        self.write_config_to_file = mock.patch(
            'chroma_agent.action_plugins.manage_corosync.write_config_to_file').start()

        mock.patch('chroma_agent.action_plugins.manage_pacemaker.unconfigure_pacemaker').start()

        old_set_address = CorosyncRingInterface.set_address

        def set_address(obj, address, prefix):
            if self.interfaces[obj.name]['ipv4_address'] is None:
                self.interfaces[obj.name]['ipv4_address'] = address
                self.interfaces[obj.name]['ipv4_netmask'] = prefix
            old_set_address(obj, address, prefix)
        mock.patch('chroma_agent.lib.corosync.CorosyncRingInterface.set_address',
                   set_address).start()

        @property
        def has_link(obj):
            return self.interfaces[obj.name]['link_up']
        self.link_patcher = mock.patch('chroma_agent.lib.corosync.CorosyncRingInterface.has_link',
                                       has_link)
        self.link_patcher.start()

        mock.patch('chroma_agent.lib.corosync.find_unused_port', return_value = 4242).start()

        mock.patch('chroma_agent.lib.corosync.discover_existing_mcastport').start()

        self.conf_template = env.get_template('corosync.conf')

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        if self.old_ethtool:
            sys.modules['ethtool'] = self.old_ethtool

    def _ring_iface_info(self):
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
        return interfaces

    def _render_test_config(self):
        return self.conf_template.render(interfaces=self._ring_iface_info())

    def test_manual_ring1_config(self):
        ring0_name = 'eth0.1.1?1b34*430'
        ring1_name = 'eth1'
        ring1_ipaddr = '10.42.42.42'
        ring1_netmask = '255.255.255.0'
        old_mcast_port = None
        new_mcast_port = '4242'

        # add shell commands to be expected
        self.add_commands(CommandCaptureCommand(('/sbin/ip', 'link', 'set', 'dev', ring1_name, 'up')),
                          CommandCaptureCommand(('/sbin/ip', 'addr', 'add', '%s/%s' % (ring1_ipaddr, ring1_netmask), 'dev', ring1_name)),
                          CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '%s:udp' % new_mcast_port)),
                          CommandCaptureCommand(('service', 'iptables', 'status'), rc=2))

        # now a two-step process! first network...
        configure_network(ring0_name, ring1_name=ring1_name,
                          ring1_ipaddr=ring1_ipaddr, ring1_prefix=ring1_netmask)

        self.write_ifcfg.assert_called_with(ring1_name, 'ba:db:ee:fb:aa:af', '10.42.42.42', '255.255.255.0')
        self.unmanage_network.assert_called_with(ring1_name, 'ba:db:ee:fb:aa:af')

        # ...then corosync
        configure_corosync(ring0_name, ring1_name, old_mcast_port, new_mcast_port)

        test_config = self._render_test_config()
        self.write_config_to_file.assert_called_with('/etc/corosync/corosync.conf', test_config)

        self.assertRanAllCommandsInOrder()

    def test_manual_ring1_config_corosync2(self):

        ring0_name = 'eth0.1.1?1b34*430'
        ring1_name = 'eth1'
        ring1_ipaddr = '10.42.42.42'
        ring1_netmask = '255.255.255.0'
        mcast_port = '4242'
        new_node_fqdn = 'servera.somewhere.org'
        pcs_password = 'bondJAMESbond'

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

        # add shell commands to be expected
        self.add_commands(CommandCaptureCommand(("/sbin/ip", "link", "set", "dev", ring1_name, "up")),
                          CommandCaptureCommand(("/sbin/ip", "addr", "add", '/'.join([ring1_ipaddr, ring1_netmask]), "dev", ring1_name)),
                          CommandCaptureCommand(("bash", "-c", "echo bondJAMESbond | passwd --stdin hacluster")),
                          CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '%s:udp' % mcast_port)),
                          CommandCaptureCommand(('service', 'iptables', 'status'), rc=0, stdout=chain_output),
                          CommandCaptureCommand(('/sbin/iptables', '-I', 'INPUT', '4', '-m', 'state', '--state',
                                                 'new', '-p', 'udp', '--dport', mcast_port, '-j', 'ACCEPT')),
                          CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '2224:tcp')),
                          CommandCaptureCommand(('service', 'iptables', 'status'), rc=0, stdout=chain_output),
                          CommandCaptureCommand(('/sbin/iptables', '-I', 'INPUT', '4', '-m', 'state', '--state',
                                                 'new', '-p', 'tcp', '--dport', '2224', '-j', 'ACCEPT')),
                          CommandCaptureCommand(("/sbin/service", "pcsd", "start")),
                          CommandCaptureCommand(("/sbin/service", "pcsd", "status")),
                          CommandCaptureCommand(('/sbin/chkconfig', 'corosync', 'on')),
                          CommandCaptureCommand(('/sbin/chkconfig', 'pcsd', 'on')),
                          CommandCaptureCommand(tuple(["pcs", "cluster", "auth"] + [new_node_fqdn] + ["-u", "hacluster", "-p", "bondJAMESbond"])))

        # now a two-step process! first network...
        configure_network(ring0_name, ring1_name=ring1_name, ring1_ipaddr=ring1_ipaddr,
                          ring1_prefix=ring1_netmask)

        self.write_ifcfg.assert_called_with(ring1_name, 'ba:db:ee:fb:aa:af', '10.42.42.42',
                                            '255.255.255.0')

        # fetch ring info
        r0, r1 = self._ring_iface_info()

        # add shell commands to be expected populated with ring interface info
        self.add_command(("pcs", "cluster", "setup",
                         "--name", "lustre-ha-cluster",
                         "--force", new_node_fqdn,
                         "--transport", "udp",
                         "--rrpmode", "passive",
                         "--addr0", str(r0.bindnetaddr),
                         "--mcast0", str(r0.mcastaddr),
                         "--mcastport0", str(r0.mcastport),
                         "--addr1", str(r1.bindnetaddr),
                         "--mcast1", str(r1.mcastaddr),
                         "--mcastport1", str(r1.mcastport),
                         "--token", "5000",
                         "--fail_recv_const", "10"))

        # ...then corosync / pcsd
        configure_corosync2_stage_1(mcast_port, pcs_password)
        configure_corosync2_stage_2(ring0_name, ring1_name, new_node_fqdn, mcast_port, pcs_password, True)

        self.assertRanAllCommandsInOrder()

    @mock.patch.object(tempfile, 'mkstemp')
    @mock.patch.object(shutil, 'move')
    @mock.patch.object(os, 'fdopen')
    def test_unconfigure_corosync2(self, mock_mkstemp, mock_move, mock_fdopen):

        from sys import version_info
        if version_info[0] == 2:
            import __builtin__ as builtins  # pylint:disable=import-error
        else:
            import builtins  # pylint:disable=import-error

        host_fqdn = "serverb.somewhere.org"
        mcast_port = "4242"

        # add shell commands to be expected
        self.add_commands(CommandCaptureCommand(('/sbin/chkconfig', 'corosync', 'off')),
                          CommandCaptureCommand(('pcs', 'status', 'nodes', 'corosync')),
                          CommandCaptureCommand(('pcs', '--force', 'cluster', 'node', 'remove', host_fqdn)),
                          CommandCaptureCommand(('service', 'iptables', 'status')),
                          CommandCaptureCommand(('/sbin/iptables', '-D', 'INPUT', '-m', 'state', '--state',
                                                 'new', '-p', 'tcp', '--dport', '2224', '-j', 'ACCEPT')),
                          CommandCaptureCommand(('service', 'iptables', 'status')),
                          CommandCaptureCommand(('/sbin/iptables', '-D', 'INPUT', '-m', 'state', '--state',
                                                 'new', '-p', 'udp', '--dport', mcast_port, '-j', 'ACCEPT')))

        # mock built-in 'open' to avoid trying to read local filesystem
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data='mock data')):
            unconfigure_corosync2(host_fqdn, mcast_port)

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

    def test_failed_has_link(self):
        self.link_patcher.stop()

        mock.patch('chroma_agent.lib.corosync.CorosyncRingInterface.__getattr__',
                   return_value=False).start()

        import errno

        def boom(*args):
            # EMULTIHOP is what gets raised with IB interfaces
            raise IOError(errno.EMULTIHOP)

        mock.patch('fcntl.ioctl', side_effect=boom).start()

        from chroma_agent.lib.corosync import get_ring0
        iface = get_ring0()

        # add shell commands to be expected
        self.add_commands(CommandCaptureCommand(('/sbin/ip', 'link', 'set', 'dev', iface.name, 'up')),
                          CommandCaptureCommand(('/sbin/ip', 'link', 'set', 'dev', iface.name, 'down')))

        self.assertFalse(iface.has_link)

        self.assertRanAllCommandsInOrder()
