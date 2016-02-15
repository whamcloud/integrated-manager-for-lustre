import tempfile
import mock
import abc

from chroma_agent.chroma_common.lib.firewall_control import FirewallControl
from chroma_agent.chroma_common.lib.firewall_control import FirewallControlEL6
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand


class BaseTestFC:
    """ Dummy class to stop encapsulated abstract classes from being run by test runner """
    def __init__(self):
        pass

    class BaseTestFirewallControl(CommandCaptureTestCase):
        """ Abstract base class for testing the FirewallControl class """
        __metaclass__ = abc.ABCMeta

        # class variables
        port = '88'
        proto = 'tcp'
        desc = 'test service'
        address = '192.168.1.100'

        # create example named tuple to compare with objects in rules list
        example_port_rule = FirewallControl.firewall_rule(port, proto, desc, persist=True, address=None)
        example_address_rule = FirewallControl.firewall_rule(0, proto, desc, persist=False, address=address)

        # base expected error strings
        assert_address_with_port_msg = 'ing a specific port on a source address is not ' \
                                       'supported, port value must be 0 (ANY)'
        assert_address_persist_msg = 'ing all ports on a source address permanently is not ' \
                                     'currently supported'
        assert_port_not_persist_msg = 'ing a single port temporarily is not currently supported'

        def init_firewall(self, el_version):
            self.el_version = el_version

        def setUp(self):
            super(BaseTestFC.BaseTestFirewallControl, self).setUp()

            mock.patch('chroma_agent.chroma_common.lib.firewall_control.platform.system',
                       return_value='Linux').start()
            mock.patch('chroma_agent.chroma_common.lib.firewall_control.platform.linux_distribution',
                       return_value=('CentOS', self.el_version, 'Final')).start()

            self.test_firewall = FirewallControl.create()

            #self.addCleanup(mock.patch.stopall())

        def test_open_address_incorrect_port(self):
            # test opening a given port on a specific address, AssertionError should be
            # thrown and no commands issued
            try:
                self.test_firewall.add_rule(1234, self.proto, self.desc, persist=True, address=self.address)
                # shouldn't get here
                self.assertTrue(False)
            except AssertionError as e:
                self.assertEqual(str(e), 'open' + self.assert_address_with_port_msg)

            # class instance should have record of added rule
            self.assertEqual(len(self.test_firewall.rules), 0)
            # no commands should have run
            self.assertRanAllCommandsInOrder()

        def test_close_address_incorrect_port(self):
            # test closing a given port on a specific address, AssertionError should be
            # thrown and no commands issued
            try:
                self.test_firewall.remove_rule(1234, self.proto, self.desc, persist=True, address=self.address)
                # shouldn't get here
                self.assertTrue(False)
            except AssertionError as e:
                self.assertEqual(str(e), 'clos' + self.assert_address_with_port_msg)

            # class instance should have record of added rule
            self.assertEqual(len(self.test_firewall.rules), 0)
            # no commands should have run
            self.assertRanAllCommandsInOrder()

        def test_open_address_persistent(self):
            # test opening all ports on a specific address permanently, AssertionError
            # should be thrown and no commands issued
            try:
                self.test_firewall.add_rule(0, self.proto, self.desc, persist=True, address=self.address)
                # shouldn't get here
                self.assertTrue(False)
            except AssertionError as e:
                self.assertEqual(str(e), 'open' + self.assert_address_persist_msg)

            # class instance should have record of added rule
            self.assertEqual(len(self.test_firewall.rules), 0)
            # no commands should have run
            self.assertRanAllCommandsInOrder()

        def test_close_address_persistent(self):
            # test closing all ports on a specific address permanently, AssertionError
            # should be thrown and no commands issued
            try:
                self.test_firewall.remove_rule(0, self.proto, self.desc, persist=True, address=self.address)
                # shouldn't get here
                self.assertTrue(False)
            except AssertionError as e:
                self.assertEqual(str(e), 'clos' + self.assert_address_persist_msg)

            # class instance should have record of added rule
            self.assertEqual(len(self.test_firewall.rules), 0)
            # no commands should have run
            self.assertRanAllCommandsInOrder()

        def test_open_port_not_persistent(self):
            # test opening port on a specific address temporarily, AssertionError
            # should be thrown and no commands issued
            try:
                self.test_firewall.add_rule(1234, self.proto, self.desc, persist=False, address=None)
                # shouldn't get here
                self.assertTrue(False)
            except AssertionError as e:
                self.assertEqual(str(e), 'open' + self.assert_port_not_persist_msg)

            # class instance should have record of added rule
            self.assertEqual(len(self.test_firewall.rules), 0)
            # no commands should have run
            self.assertRanAllCommandsInOrder()

        def test_close_port_not_persistent(self):
            # test closing port on a specific address temporarily, AssertionError
            # should be thrown and no commands issued
            try:
                self.test_firewall.remove_rule(1234, self.proto, self.desc, persist=False, address=None)
                # shouldn't get here
                self.assertTrue(False)
            except AssertionError as e:
                self.assertEqual(str(e), 'clos' + self.assert_port_not_persist_msg)

            # class instance should have record of added rule
            self.assertEqual(len(self.test_firewall.rules), 0)
            # no commands should have run
            self.assertRanAllCommandsInOrder()

        @abc.abstractmethod
        def test_open_port(self):
            raise NotImplementedError

        @abc.abstractmethod
        def test_close_port(self):
            raise NotImplementedError

        @abc.abstractmethod
        def test_open_address(self):
            raise NotImplementedError

        @abc.abstractmethod
        def test_close_address(self):
            raise NotImplementedError


class TestFirewallControlEL6(BaseTestFC.BaseTestFirewallControl):

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

    # example output from 'iptables -L' or 'service iptables status' with matching rule at different index
    different_index_output = """Table: filter
Chain INPUT (policy ACCEPT)
num  target     prot opt source               destination
1    ACCEPT     all  --  0.0.0.0/0            0.0.0.0/0           state RELATED,ESTABLISHED
2    ACCEPT     icmp --  0.0.0.0/0            0.0.0.0/0
3    ACCEPT     all  --  0.0.0.0/0            0.0.0.0/0
4    ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0           state NEW tcp dpt:22
5    ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0           state NEW tcp dpt:80
6    ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0           state NEW tcp dpt:443
7    ACCEPT     udp  --  0.0.0.0/0            0.0.0.0/0           state NEW udp dpt:123
8    REJECT     all  --  0.0.0.0/0            0.0.0.0/0           reject-with icmp-host-prohibited

Chain FORWARD (policy ACCEPT)
num  target     prot opt source               destination
1    REJECT     all  --  0.0.0.0/0            0.0.0.0/0           reject-with icmp-host-prohibited

Chain OUTPUT (policy ACCEPT)
num  target     prot opt source               destination

"""

    # example output from 'iptables -L' or 'service iptables status' if firewall not configured
    not_configured_output = """Table: filter
Chain INPUT (policy ACCEPT)
num  target     prot opt source               destination

Chain FORWARD (policy ACCEPT)
num  target     prot opt source               destination

Chain OUTPUT (policy ACCEPT)
num  target     prot opt source               destination

"""

    not_running_msg = 'iptables: Firewall is not running.'

    def __init__(self, *args, **kwargs):
        super(TestFirewallControlEL6, self).__init__(*args, **kwargs)
        self.init_firewall('6.6')

    def test_open_port(self):
        # test opening a port, commands should be issued in order and the rule should be
        # recorded in 'rules' member of FirewallControl class instance
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.add_commands(
            CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '%s:%s' % (self.port,
                                                                              self.proto))),
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.chain_output),
            CommandCaptureCommand(('/sbin/iptables', '-I', 'INPUT', '4', '-m', 'state', '--state',
                                   'new', '-p', self.proto, '--dport', self.port, '-j', 'ACCEPT')))

        response = self.test_firewall.add_rule(self.port, self.proto, self.desc, persist=True)

        # class instance should have record of added rule
        self.assertEqual(len(self.test_firewall.rules), 1)
        self.assertEqual(self.test_firewall.rules[0], self.example_port_rule)
        # None return value indicates success
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    @mock.patch.object(tempfile, 'mkstemp')
    def test_close_port(self, mock_mkstemp):
        # test closing a port, method includes file operations within a try clause which we
        # break from by raising an exception in the patched object. test only shell commands here
        e = IOError('abc')
        mock_mkstemp.side_effect = e

        self.add_commands(
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.chain_output),
            CommandCaptureCommand(('/sbin/iptables', '-D', 'INPUT', '-m', 'state', '--state',
                                   'new', '-p', self.proto, '--dport', self.port, '-j', 'ACCEPT')))

        try:
            self.test_firewall.remove_rule(self.port, self.proto, self.desc, persist=True)
            # this line should not be executed, we should receive an exception from the mock
            self.assertTrue(False)
        except IOError as e:
            self.assertTrue(e.args[0], 'abc')

        self.assertRanAllCommandsInOrder()

    @mock.patch.object(FirewallControlEL6, '_remove_port', return_value=0)
    def test_close_removes_rule(self, mock__remove_port):
        # test closing a port removes a rule from the class instance 'rules' list,
        # this is additionally required because test_close_port exits remove() before rule is
        # removed from list (intentionally thrown exception)

        # add rule object so we can test it is removed when we issue the remove() command
        self.test_firewall.rules.append(self.example_port_rule)
        self.assertEqual(len(self.test_firewall.rules), 1)

        # commands won't actually be issued because of the mock patch, example rule should be
        # removed from 'rules' list
        response = self.test_firewall.remove_rule(self.port, self.proto, self.desc, persist=True)

        # None return value indicates success
        self.assertEqual(response, None)
        # rule should have been removed from list
        self.assertEqual(len(self.test_firewall.rules), 0)

    def test_open_address(self):
        # test opening all ports on a specific address, commands should be issued in order and the
        # rule should be recorded in 'rules' member of FirewallControl class instance
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.add_commands(
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.chain_output),
            CommandCaptureCommand(('/sbin/iptables', '-I', 'INPUT', '4', '-m', 'state', '--state',
                                   'NEW', '-m', self.proto, '-p', self.proto, '-d', self.address,
                                   '-j', 'ACCEPT')))

        response = self.test_firewall.add_rule(0, self.proto, self.desc, persist=False, address=self.address)

        # class instance should have record of added rule
        self.assertEqual(len(self.test_firewall.rules), 1)
        self.assertEqual(self.test_firewall.rules[0], self.example_address_rule)
        # None return value indicates success
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    def test_close_address(self):
        # test remove_rule with address removes relevant rule from the class instance 'rules' list,
        # also test correct shell command is issued

        # add rule object so we can test it is removed when we issue the remove() command
        self.test_firewall.rules.append(self.example_address_rule)
        self.assertEqual(len(self.test_firewall.rules), 1)

        self.add_commands(
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.chain_output),
            CommandCaptureCommand(('/sbin/iptables', '-D', 'INPUT', '-m', 'state', '--state',
                                   'NEW', '-m', self.proto, '-p', self.proto, '-d', self.address,
                                   '-j', 'ACCEPT')))

        response = self.test_firewall.remove_rule(0, self.proto, self.desc, persist=False, address=self.address)

        # None return value indicates success
        self.assertEqual(response, None)
        # rule should have been removed from list
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.assertRanAllCommandsInOrder()

    def test_add_existing_port_rule(self):
        # rules are analysed to check they don't match existing entries, test that additional
        # rules are not added
        self.add_commands(
            CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '%s:%s' % ('123', 'udp'))),
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.chain_output))

        response = self.test_firewall.add_rule('123', 'udp', 'test_service', persist=True)

        # None return value indicates success or no action performed
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    def test_add_existing_port_rule_different_index(self):
        # rules are analysed to check they don't match existing entries at different index,
        # test that additional rules are not added
        self.add_commands(
            CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '%s:%s' % ('123', 'udp'))),
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.different_index_output))

        response = self.test_firewall.add_rule('123', 'udp', 'test_service', persist=True)

        # None return value indicates success or no action performed
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    def test_firewall_not_running(self):
        # if the firewall is not running, add_rule should silently exit while logging a warning
        # test that we return None in this situation
        self.add_commands(
            CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '%s:%s' % ('123', 'udp'))),
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.not_running_msg, rc=3))

        response = self.test_firewall.add_rule('123', 'udp', 'test_service', persist=True)

        # None return value indicates success or no action performed
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    def test_firewall_not_configured(self):
        # if the firewall is not configured, add_rule should silently exit while logging a warning
        # test that we return None in this situation
        self.add_commands(
            CommandCaptureCommand(('/usr/sbin/lokkit', '-n', '-p', '%s:%s' % ('123', 'udp'))),
            CommandCaptureCommand(('service', 'iptables', 'status'), stdout=self.not_configured_output, rc=3))

        response = self.test_firewall.add_rule('123', 'udp', 'test_service', persist=True)

        # None return value indicates success or no action performed
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()


class TestFirewallControlEL7(BaseTestFC.BaseTestFirewallControl):

    not_running_msg = 'FirewallD is not running'

    def __init__(self, *args, **kwargs):
        super(TestFirewallControlEL7, self).__init__(*args, **kwargs)
        self.init_firewall('7.2')

    def test_open_port(self):
        # test opening a port, commands should be issued in order and the rule should be
        # recorded in 'rules' member of FirewallControl class instance
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.add_commands(
            CommandCaptureCommand(('/usr/bin/firewall-cmd',
                                   '--add-port=%s/%s' % (self.port, self.proto))),
            CommandCaptureCommand(('/usr/bin/firewall-cmd',
                                   '--add-port=%s/%s' % (self.port, self.proto),
                                   '--permanent')))

        response = self.test_firewall.add_rule(self.port, self.proto, self.desc, persist=True)

        # class instance should have record of added rule
        self.assertEqual(len(self.test_firewall.rules), 1)
        self.assertEqual(self.test_firewall.rules[0], self.example_port_rule)
        # None return value indicates success
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    def test_close_port(self):
        # test closing a port, commands should be issued in order and the rule should be
        # removed from 'rules' member of FirewallControl class instance

        # add rule object so we can test it is removed when we issue the remove() command
        self.test_firewall.rules.append(self.example_port_rule)
        self.assertEqual(len(self.test_firewall.rules), 1)

        self.add_commands(
            CommandCaptureCommand(('/usr/bin/firewall-cmd',
                                   '--remove-port=%s/%s' % (self.port, self.proto))),
            CommandCaptureCommand(('/usr/bin/firewall-cmd',
                                   '--remove-port=%s/%s' % (self.port, self.proto),
                                   '--permanent')))

        response = self.test_firewall.remove_rule(self.port, self.proto, self.desc, persist=True)

        # None return value indicates success
        self.assertEqual(response, None)
        # rule should have been removed from list
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.assertRanAllCommandsInOrder()

    def test_open_address(self):
        # test opening all ports on a specific address, commands should be issued in order and the
        # rule should be recorded in 'rules' member of FirewallControl class instance
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.add_commands(
            CommandCaptureCommand(('/usr/bin/firewall-cmd', '--add-rich-rule='
                                                            'rule family="ipv4" '
                                                            'destination address="%s" '
                                                            'protocol value="%s" '
                                                            'accept' % (self.address, self.proto))))

        response = self.test_firewall.add_rule(0, self.proto, self.desc, persist=False,
                                               address=self.address)

        # None return value indicates success
        self.assertEqual(response, None)
        # class instance should have record of added rule
        self.assertEqual(len(self.test_firewall.rules), 1)
        self.assertEqual(self.test_firewall.rules[0], self.example_address_rule)
        self.assertRanAllCommandsInOrder()

    def test_close_address(self):
        # test remove_rule with address removes relevant rule from the class instance 'rules' list,
        # also test correct shell command is issued

        # add rule object so we can test it is removed when we issue the remove() command
        self.test_firewall.rules.append(self.example_address_rule)
        self.assertEqual(len(self.test_firewall.rules), 1)

        self.add_commands(
            CommandCaptureCommand(('/usr/bin/firewall-cmd', '--remove-rich-rule='
                                                            'rule family="ipv4" '
                                                            'destination address="%s" '
                                                            'protocol value="%s" '
                                                            'accept' % (self.address, self.proto))))

        response = self.test_firewall.remove_rule(0, self.proto, self.desc, persist=False, address=self.address)

        # None return value indicates success
        self.assertEqual(response, None)
        # rule should have been removed from list
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.assertRanAllCommandsInOrder()

    def test_firewall_not_running(self):
        # if the firewall is not running, add_rule should silently exit while logging a warning
        # test that we return None in this situation
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.add_command(('/usr/bin/firewall-cmd', '--add-port=%s/%s' % (self.port, self.proto)),
                         rc=252, stdout=self.not_running_msg)

        response = self.test_firewall.add_rule(self.port, self.proto, self.desc, persist=True)

        # class instance should have record of added rule
        self.assertEqual(len(self.test_firewall.rules), 0)
        # None return value indicates success
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()
