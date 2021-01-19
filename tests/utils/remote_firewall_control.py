# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import abc
from collections import namedtuple
from operator import attrgetter
from emf_common.lib import util
import re


class RemoteFirewallControl(object):
    """Class for issuing shell commands for managing the firewall, this abstract base class is subclassed to
    provide concrete implementations of the abstract methods containing the distribution specific command parameters
    """

    class_override = None
    __metaclass__ = abc.ABCMeta

    class_priority = None
    firewall_list_cmd = None
    firewall_app_name = None
    remote_access_func = None

    # dict of RemoteFirewallControl objects for specific servers,  defaults to empty string which evaluates as False
    controller_instances = {}

    firewall_rule = namedtuple("firewall_rule", ("port", "protocol"))

    def __init__(self, address, remote_access_func):
        self.address = address
        self.remote_access_func = remote_access_func
        self.rules = []

    @classmethod
    def _applicable(cls, address, remote_access_func):
        """
        Verify applicability of RemoteFirewallControl subclass by testing installed firewall control packages
        choosing class based on a numerical priority value

        :param address: remote server IP address to verify
        :param remote_access_func: reference to function which provides remote access shell execution and returns
                                   RunResult object
        :return: true if applicable, false if not
        """
        return remote_access_func(address, "which %s" % cls.firewall_app_name).rc == 0

    @classmethod
    def create(cls, address, remote_access_func):
        """ check cache for controller at this address, update if necessary and return controller object """
        if address not in cls.controller_instances:
            # Note: this assumes OS will not be changed on a remote host during parent process lifetime
            try:
                # return available class with highest priority (positive integer closest to 0)
                # Note: if identical class_priority values exist in resultant list, either class could be returned
                required_class = sorted(
                    [_cls for _cls in util.all_subclasses(cls) if _cls._applicable(address, remote_access_func)],
                    key=attrgetter("class_priority"),
                )[0]
            except IndexError:
                raise RuntimeError("Current platform version not applicable")

            cls.controller_instances[address] = required_class(address, remote_access_func)

        return cls.controller_instances[address]

    @abc.abstractmethod
    def process_rules(self):
        """ process output from firewall application as input to create member list of rule objects """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def remote_add_port_cmd(port, proto):
        """ return string representation of bash command to add port on a remote firewall """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def remote_remove_port_cmd(port, proto):
        """ return string representation of bash command to remove port on a remote firewall """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def remote_validate_persistent_rule_cmd(port):
        """ return string representation of bash command to check for existence of port entry in firewall config """
        raise NotImplementedError


class RemoteFirewallControlIpTables(RemoteFirewallControl):
    """ subclass of FirewallControl extended with functionality to enable remote firewall management with iptables """

    class_priority = 2

    # iptables utility may coexist with firewall-cmd, lokkit is less likely to and therefore test its presence
    firewall_app_name = "lokkit"

    # test firewall command used to identify firewall application running on remote server
    firewall_list_cmd = "iptables -L INPUT -nv"

    def process_rules(self):
        """
        Process string from iptables application output on EL6, matches ANY source/dest address rule specifications

        :return: None on success/valid input, error string otherwise
        """
        result = self.remote_access_func(self.address, self.firewall_list_cmd)

        if result.rc != 0:
            raise RuntimeError("process_rules(): remote shell command failed unexpectedly, is iptables running?")

        lines = result.stdout.split("\n")

        try:
            # identify the beginning index of the table
            index = next(lines.index(line) for line in lines if line.startswith("Chain INPUT (policy ACCEPT"))

        except StopIteration:
            raise RuntimeError(
                'process_rules(): "%s" command output contains unexpected iptables output' % self.firewall_list_cmd
            )

        # as we are reading in a new firewall table content, reset 'rules' member list
        self.rules = []

        # specify regex pattern to match all address port rules which we are interested in
        pattern = " +ACCEPT +(?P<proto>(all|udp|tcp)) +.*(0.0.0.0\/0 +){2}state NEW (all|udp|tcp) dpt:(?P<port>\d+)"

        # process all rules within the input chain table until any 'REJECT' rules as we can't reliably
        # assume 'ACCEPT' rules after a 'REJECT' rule will behave as we expect without further analysis
        while lines[index].strip() != "" and lines[index].split()[1] != "REJECT":
            match = re.search(pattern, lines[index])

            if match:
                # Note: because we are uncertain about the command used to obtain the input string, assume persist=False
                self.rules.append(self.firewall_rule(match.group("port"), match.group("proto")))
            index += 1

        return None

    @staticmethod
    def remote_add_port_cmd(port, proto):
        """ return string representation of bash command to add port on a remote firewall """
        return "lokkit --port=%s:%s --update" % (port, proto)

    @staticmethod
    def remote_remove_port_cmd(port, proto):
        """
        return string representation of bash command to remove port on a remote firewall, matching rule is
        removed in iptables, although this is effective immediately, save configuration so removed rule is not
        reinstated on iptables reload (lokkit added rule matches this rule-spec)
        """
        return "iptables -D INPUT -m state --state new -p %s --dport %s -j ACCEPT && iptables-save" % (proto, port)

    @staticmethod
    def remote_validate_persistent_rule_cmd(port):
        """ return string representation of bash command to check for existence of port entry in firewall config """
        return 'grep -e "{0}{1}\|{2}{1}" {3} {4}'.format(
            "--dport ", port, "--port=", "/etc/sysconfig/iptables", "/etc/sysconfig/system-config-firewall"
        )


class RemoteFirewallControlFirewallCmd(RemoteFirewallControl):
    """
    subclass of FirewallControl extended with functionality to enable remote firewall management with firewall-cmd
    """

    class_priority = 1

    firewall_app_name = "firewall-cmd"

    # test firewall command used to identify firewall application running on remote server
    firewall_list_cmd = "firewall-cmd --list-ports"

    def process_rules(self):
        """
        Process string from firewall-cmd application output on EL7, matches ANY source/dest address rule specifications

        Note: the expected input is line separated <port>/<proto> pairs, this will give any explicitly allowed rules
        added by EMF and other applications to the default zone but will not list named services enabled in firewalld
        Empty string is a valid input indicating no explicitly added port/proto rules

        :return: None on success/valid input, error string otherwise
        """
        result = self.remote_access_func(self.address, self.firewall_list_cmd)

        if result.rc != 0:
            from emf_common.lib.shell import Shell

            raise RuntimeError(
                """process_rules(): remote shell command failed unexpectedly (%s), is firewall-cmd running? (%s) (%s)
systemctl status firewalld:
%s

systemctl status polkit:
%s

journalctl -n 100:
%s"""
                % (
                    result.rc,
                    result.stdout,
                    result.stderr,
                    Shell.run(["systemctl", "status", "firewalld"]).stdout,
                    Shell.run(["systemctl", "status", "polkit"]).stdout,
                    Shell.run(["journalctl", "-n", "100"]).stdout,
                )
            )

        if result.stdout.strip() == "":
            return None

        # handle output separated by either new-line chars, spaces, or both
        tokens = [token for token in result.stdout.replace("\n", " ").split() if token]

        # as we are reading in a new firewall table content, reset 'rules' member list
        self.rules = []
        index = 0

        while index < len(tokens):
            match = re.search("(?P<port>\d+)\/(?P<proto>\w+)", tokens[index])

            if match:
                # Note: because we are uncertain about the command used to obtain the input string, assume persist=False
                self.rules.append(self.firewall_rule(match.group("port"), match.group("proto")))
            else:
                raise RuntimeError(
                    'process_rules(): "%s" command output contains unexpected firewall-cmd output'
                    % self.firewall_list_cmd
                )

            index += 1

        return None

    @staticmethod
    def remote_add_port_cmd(port, proto):
        """ return string representation of bash command to add port on a remote firewall """
        return 'for i in "" "--permanent"; do ' "/usr/bin/firewall-cmd --add-port=%s/%s $i; " "done" % (port, proto)

    @staticmethod
    def remote_remove_port_cmd(port, proto):
        """ return string representation of bash command to remove port on a remote firewall """
        return 'for i in "" "--permanent"; do ' "/usr/bin/firewall-cmd --remove-port=%s/%s $i; " "done" % (port, proto)

    @staticmethod
    def remote_validate_persistent_rule_cmd(port):
        """ return string representation of bash command to check for existence of port entry in firewall config """
        return "/usr/bin/firewall-cmd --list-ports --permanent | grep %s" % port
