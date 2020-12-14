import mock
import abc

from iml_common.lib import util
from iml_common.lib.firewall_control import FirewallControl
from iml_common.test.command_capture_testcase import CommandCaptureTestCase
from iml_common.test.command_capture_testcase import CommandCaptureCommand


class BaseTestFC:
    """ Dummy class to stop encapsulated abstract classes from being run by test runner """

    def __init__(self):
        pass

    class BaseTestFirewallControl(CommandCaptureTestCase):
        """ Abstract base class for testing the FirewallControl class """

        __metaclass__ = abc.ABCMeta

        # class variables
        port = "88"
        proto = "tcp"
        desc = "test service"
        address = "192.168.1.100"

        # create example named tuple to compare with objects in rules list
        example_port_rule = FirewallControl.FirewallRule(port, proto, desc, persist=True, address=None)
        example_address_rule = FirewallControl.FirewallRule(0, proto, desc, persist=False, address=address)

        # base expected error strings
        assert_address_with_port_msg = (
            "ing a specific port on a source address is not " "supported, port value must be 0 (ANY)"
        )
        assert_address_persist_msg = "ing all ports on a source address permanently is not " "currently supported"
        assert_port_not_persist_msg = "ing a single port temporarily is not currently supported"

        def init_firewall(self, el_version):
            self.el_version = el_version

        def setUp(self):
            super(BaseTestFC.BaseTestFirewallControl, self).setUp()

            mock.patch.object(
                util, "platform_info", util.PlatformInfo("Linux", "CentOS", 0.0, self.el_version, 0.0, 0, "")
            ).start()

            self.test_firewall = FirewallControl.create()

            # Guaranteed cleanup with unittest2
            self.addCleanup(mock.patch.stopall)

        def test_open_address_incorrect_port(self):
            # test opening a given port on a specific address, AssertionError should be
            # thrown and no commands issued
            try:
                self.test_firewall.add_rule(1234, self.proto, self.desc, persist=True, address=self.address)
                # shouldn't get here
                self.assertTrue(False)
            except AssertionError as e:
                self.assertEqual(str(e), "open" + self.assert_address_with_port_msg)

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
                self.assertEqual(str(e), "clos" + self.assert_address_with_port_msg)

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
                self.assertEqual(str(e), "open" + self.assert_address_persist_msg)

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
                self.assertEqual(str(e), "clos" + self.assert_address_persist_msg)

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
                self.assertEqual(str(e), "open" + self.assert_port_not_persist_msg)

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
                self.assertEqual(str(e), "clos" + self.assert_port_not_persist_msg)

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


class TestFirewallControlEL7(BaseTestFC.BaseTestFirewallControl):

    not_running_msg = "FirewallD is not running"

    def __init__(self, *args, **kwargs):
        super(TestFirewallControlEL7, self).__init__(*args, **kwargs)
        self.init_firewall("7.X")

    def test_open_port(self):
        # test opening a port, commands should be issued in order and the rule should be
        # recorded in 'rules' member of FirewallControl class instance
        self.assertEqual(len(self.test_firewall.rules), 0)
        self.add_commands(
            CommandCaptureCommand(("/usr/bin/firewall-cmd", "--add-port=%s/%s" % (self.port, self.proto))),
            CommandCaptureCommand(
                ("/usr/bin/firewall-cmd", "--add-port=%s/%s" % (self.port, self.proto), "--permanent")
            ),
        )

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
            CommandCaptureCommand(("/usr/bin/firewall-cmd", "--remove-port=%s/%s" % (self.port, self.proto))),
            CommandCaptureCommand(
                ("/usr/bin/firewall-cmd", "--remove-port=%s/%s" % (self.port, self.proto), "--permanent")
            ),
        )

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
            CommandCaptureCommand(
                (
                    "/usr/bin/firewall-cmd",
                    "--add-rich-rule="
                    'rule family="ipv4" '
                    'destination address="%s" '
                    'protocol value="%s" '
                    "accept" % (self.address, self.proto),
                )
            )
        )

        response = self.test_firewall.add_rule(0, self.proto, self.desc, persist=False, address=self.address)

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
            CommandCaptureCommand(
                (
                    "/usr/bin/firewall-cmd",
                    "--remove-rich-rule="
                    'rule family="ipv4" '
                    'destination address="%s" '
                    'protocol value="%s" '
                    "accept" % (self.address, self.proto),
                )
            )
        )

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
        self.add_command(
            ("/usr/bin/firewall-cmd", "--add-port=%s/%s" % (self.port, self.proto)), rc=252, stdout=self.not_running_msg
        )

        response = self.test_firewall.add_rule(self.port, self.proto, self.desc, persist=True)

        # class instance should have record of added rule
        self.assertEqual(len(self.test_firewall.rules), 0)
        # None return value indicates success
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()
