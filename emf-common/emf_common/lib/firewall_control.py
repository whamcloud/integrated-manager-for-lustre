# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import abc
from collections import namedtuple
from ..lib import shell
from .util import enum, all_subclasses


class FirewallControl(object):
    """Class for issuing shell commands for managing the firewall, this abstract base class is subclassed to
    provide concrete implementations of the abstract methods containing the distribution specific command parameters
    """

    class_override = None
    __metaclass__ = abc.ABCMeta

    platform_use = None

    FirewallRule = namedtuple("FirewallRule", ("port", "protocol", "description", "persist", "address"))

    # identifiers for results of firewall operations
    SuccessCode = enum("UPDATED", "DUPLICATE", "NOTRUNNING", "NORULES")

    def __init__(self, logger=None):
        self.logger = logger
        self.rules = []

    def _log(self, msg, level):
        """ utility function for using reference to an external logger """
        if self.logger and hasattr(self.logger, level):
            getattr(self.logger, level)("{0}: {1}".format(self.__class__.__name__, msg))

    @classmethod
    def _applicable(cls):
        from .util import platform_info

        return (
            cls.platform_use
            and (platform_info.system == "Linux")
            and cls.platform_use == platform_info.distro_version_full.split(".")[0]
        )

    @classmethod
    def create(cls, logger=None):
        try:
            required_class = next(_cls for _cls in all_subclasses(cls) if _cls._applicable())

            return required_class(logger=logger)
        except StopIteration:
            raise RuntimeError("Current platform version not supported (supported: {})".format(all_subclasses(cls)))

    def add_rule(self, port, proto, desc, persist=True, address=None):
        """ "Open port(s) in firewall

        :param port: port number
        :param proto: protocol string eg. udp
        :param desc: description of service to be using this port
        :param address: if present, open all ports to this destination address
        :return: error string or None for success
        """
        self._log("Opening firewall for %s" % desc, "info")
        if address:
            assert port == 0, (
                "opening a specific port on a source address " "is not supported, port value must be 0 (ANY)"
            )

            assert persist is False, "opening all ports on a source address " "permanently is not currently supported"

            retval = self._add_address(address, proto)
        else:
            assert persist is True, "opening a single port temporarily is not currently supported"

            retval = self._add_port(port, proto)

        if (retval == self.SuccessCode.UPDATED) and (
            self.FirewallRule(port, proto, desc, persist, address) not in self.rules
        ):
            # only add to list if rule successfully added
            self.rules.append(self.FirewallRule(port, proto, desc, persist, address))

        # if success return code received, return None on success, otherwise return error string
        return None if (retval in self.SuccessCode.reverse_mapping.keys()) else retval

    def remove_rule(self, port, proto, desc, persist=True, address=None):
        """ "Close port(s) in firewall
        :param port: port number
        :param proto: protocol string eg. udp
        :param desc: description of service to be using this port
        :param address: if present, remove rule to open all ports to this destination address
        :return: error string or None for success
        """
        self._log("Closing firewall for %s" % desc, "info")
        if address:
            assert port == 0, (
                "closing a specific port on a source address is not " "supported, port value must be 0 (ANY)"
            )

            assert persist is False, "closing all ports on a source address permanently is not " "currently supported"

            retval = self._remove_address(address, proto)
        else:
            assert persist is True, "closing a single port temporarily is not currently supported"

            retval = self._remove_port(port, proto)

        if retval == self.SuccessCode.UPDATED:
            # only try to remove from list if rule successfully deleted
            try:
                self.rules.remove(self.FirewallRule(port, proto, desc, persist, address))
            except ValueError:
                pass

        # if success return code received, return None on success, otherwise return error string
        return None if (retval in self.SuccessCode.reverse_mapping.keys()) else retval

    @abc.abstractmethod
    def _add_port(self, port, proto):
        """ Abstract method for opening a single port (to/from all addresses) in firewall """
        raise NotImplementedError

    @abc.abstractmethod
    def _remove_port(self, port, proto):
        """Abstract method for removing rule to open a single port (to/from all addresses) in
        firewall
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _add_address(self, address, proto):
        """ Abstract method for opening all ports on a destination address in firewall """
        raise NotImplementedError

    @abc.abstractmethod
    def _remove_address(self, address, proto):
        """Abstract method for removing rule to open all ports on a destination address in
        firewall
        """
        raise NotImplementedError


class FirewallControlEL7(FirewallControl):
    """ concrete subclass of FirewallControl abstract base class for EL7 firewall control """

    platform_use = "7"

    # return code for 'FirewallD is not running'
    not_running_rc = 252
    duplicate_msg = "Warning: ALREADY_ENABLED\n"

    def _port_rule(self, act, port, proto):
        """Wrapper for port-rule firewall-cmd shell invocations. Command issued twice, once WITH
        the --permanent flag to store persistent settings, and once WITHOUT for immediate effect
        This is the recommended procedure as documented by man page

        Note: rule is activated on the default zone which is assumed is bound to public
        facing interfaces
        """
        arg_list = ["/usr/bin/firewall-cmd", "--%s-port=%s/%s" % (act, port, proto)]

        result = shell.Shell.run(arg_list)

        if result.rc:
            if result.rc == self.not_running_rc:
                # firewall service is not running, this is not an error
                return self.SuccessCode.NOTRUNNING

            return "Error (%s) running '%s': '%s' '%s'" % (result.rc, " ".join(arg_list), result.stdout, result.stderr)

        if result.stdout == self.duplicate_msg:
            return self.SuccessCode.DUPLICATE

        error = shell.Shell.run_canned_error_message(arg_list + ["--permanent"])

        return error or self.SuccessCode.UPDATED

    def _address_rule(self, act, daddress, proto):
        """Wrapper for address-rule firewall-cmd shell invocations. Command issued only for
        immediate effect, in the case of this address rule for EL7 the setting is not persistent
        as white listing all ports on a specific destination address should only be a temporary
        operation so as not to adversely affect security of the target

        Note: rule is activated on the default zone which is assumed to be bound to relevant public
        facing interfaces, rule matches traffic to a destination address on the target
        """
        # temporary firewall rich rule specification
        rich_rule_spec = 'rule family="ipv4" destination address="%s" protocol value="%s" accept' % (daddress, proto)

        # when constructing the "rich rule" instruction parameter for firewall-cmd we don't have
        # to encapsulate the rule spec in single quotes as you would in bash because shell.Shell.run
        # implicitly assumes it is a value for a single keyword argument
        arg_list = ["/usr/bin/firewall-cmd", "--%s-rich-rule=%s" % (act, rich_rule_spec)]

        result = shell.Shell.run(arg_list)

        if result.rc:
            if result.rc == self.not_running_rc:
                # firewall service is not running, this is not an error
                return self.SuccessCode.NOTRUNNING

            return "Error (%s) running '%s': '%s' '%s'" % (result.rc, " ".join(arg_list), result.stdout, result.stderr)

        if result.stdout == self.duplicate_msg:
            return self.SuccessCode.DUPLICATE

        return self.SuccessCode.UPDATED

    def _add_port(self, port, proto):
        """ EL7 implementation of opening port on firewall using linux shell """
        return self._port_rule("add", port, proto)

    def _remove_port(self, port, proto):
        """ EL7 implementation of removing rule to open port on firewall using linux shell """
        return self._port_rule("remove", port, proto)

    def _add_address(self, address, proto):
        """EL7 implementation of opening all ports to a specific address on firewall using
        linux shell
        """
        return self._address_rule("add", address, proto)

    def _remove_address(self, address, proto):
        """EL7 implementation of removing rule to open ports to a specific address on
        firewall using linux shell
        """
        return self._address_rule("remove", address, proto)
