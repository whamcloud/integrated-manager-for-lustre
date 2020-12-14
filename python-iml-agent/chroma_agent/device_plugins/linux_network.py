# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import re
import os
from collections import defaultdict
from collections import namedtuple

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import DevicePlugin


EXCLUDE_INTERFACES = ["lo"]


class NetworkInterface(object):
    """Created with an array of lines that are the output from ifconfig, this class will
    parse those lines and end up with a set of properties corresponding to the parsed data

    It only produces what is there and so some values may be left unset. The idea is that
    once parsed the results can be accessed using named properties.
    """

    RXTXStats = namedtuple("RXTXStats", ["rx_bytes", "tx_bytes"])

    def __init__(self, ip_output_lines, rx_tx_stats):
        match_values = [
            "([0-9]*):(\s*)(?P<interface>[^:]*).*",
            "(.*)link/(?P<type>[^\s]*)(\s*)(?P<mac_address>[^\s]*).*",
            "(.*)inet (?P<inet4_addr>[^/]*)/(?P<inet4_prefix>[0-9]*).*",
            "(.*)inet6 (?P<inet6_addr>[^/]*)/(?P<inet6_mask>[0-9]*).*",
            ".*(?P<slave>SLAVE).*",
            ".*(?P<up>UP).*",
        ]

        self._values = defaultdict(lambda: "")

        # Set some defaults
        self._values["up"] = "DOWN"

        for line in ip_output_lines:
            for match_value in match_values:
                m = re.match(match_value, line)
                if m:
                    self._values.update(m.groupdict())

        try:
            self.rx_tx_stats = rx_tx_stats[self.interface]
        except KeyError:
            self.rx_tx_stats = self.RXTXStats("0", "0")

    @property
    def interface(self):
        """
        :return: str: The name of the device, for example eth0 or ib2, or '' if not present.
        """
        return self._values["interface"]

    @property
    def mac_address(self):
        """
        :return: str: Containing the mac address of the device, or '' if not present.
        """
        return self._values["mac_address"]

    @property
    def type(self):
        """
        :return: str: Containing the type of the interface, ethernet for example, or '' if not present.
        """
        return self._values["type"]

    @property
    def inet4_addr(self):
        """
        :return: str: Containing the type of the inet4 address of interface, or '' if not present.
        """
        return self._values["inet4_addr"]

    @property
    def inet4_prefix(self):
        """
        :return: int: prefix len converted from the mask described by ifconfig as a slave device. Returns 32 if no prefix existed.
        """
        try:
            return int(self._values["inet4_prefix"])
        except ValueError:
            return 0

    @property
    def inet6_addr(self):
        """
        :return: str: Containing the type of the inet6 address of interface, or '' if not present.
        """
        return self._values["inet6_addr"]

    @property
    def up(self):
        """
        :return: bool: True if the device described as being by ifconfig as being in the up state
        """
        return self._values["up"].upper() == "UP"

    @property
    def slave(self):
        """
        :return: bool: True if the device described by ifconfig as a slave device
        """
        return self._values["slave"].upper() == "SLAVE"


class NetworkInterfaces(dict):
    network_translation = {"ethernet": "tcp", "ether": "tcp", "infiniband": "o2ib"}

    proc_net_dev_keys = {}

    class InterfaceNotFound(LookupError):
        pass

    def __init__(self):
        """
        :return: A dist of dicts that describe all of the network interfaces on the node with
        the exception of the the lo interface which is excluded from the list.
        """

        def interface_to_lnet_type(if_type):
            """
            To keep everything consistant we report networks types as the lnd name not the linux name we
            have to translate somewhere so do it at source, if the user ever needs to see it as Linux types
            we can translate back.
            There is a train of thought that says it if is unknown we should cause an exception which means
            the app will not work, I prefer to try an approach that says returning just the unknown might
            well work, and if not it causes an exception somewhere else.
            """
            return self.network_translation.get(if_type.lower(), if_type.lower())

        try:
            ip_out = AgentShell.try_run(["ip", "addr"])

            with open("/proc/net/dev") as file:
                dev_stats = file.readlines()
        except IOError:
            daemon_log.warning("ip: failed to run")
            return

        # Parse the ip command output and create a list of lists, where each entry is the output from one device.
        device_lines = []
        devices = [device_lines]
        for line in ip_out.split("\n"):
            if line and line[0] != " ":  # First line of a new device.
                if device_lines:
                    device_lines = []
                    devices.append(device_lines)

            device_lines.append(line)

        # Parse the /proc/net/dev output and create a dictionary of stats (just rx_byte, tx_bytes today) with an entry for each
        # network port. The input will look something like below.
        # Inter-|   Receive                                                |  Transmit
        # face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
        #    lo: 8305402   85521    0    0    0     0          0         0  8305402   85521    0    0    0     0       0          0
        #  eth0: 318398818 2069564    0    0    0     0          0         0  6622219   50337    0    0    0     0       0          0
        #  eth1:  408736    7857    0    0    0     0          0         0  4347300   35206    0    0    0     0       0          0
        if NetworkInterfaces.proc_net_dev_keys == {}:
            keys = dev_stats[1].replace("|", " ").split()
            keys = keys[1:]

            for index in range(0, len(keys)):
                NetworkInterfaces.proc_net_dev_keys[("rx_" if index < len(keys) / 2 else "tx_") + keys[index]] = (
                    index + 1
                )

        proc_net_dev_values = {}

        # Data is on the 3rd line to the end, so get the values for each entry.
        for line in dev_stats[2:]:
            values = line.split()
            proc_net_dev_values[values[0][:-1]] = NetworkInterface.RXTXStats(
                values[NetworkInterfaces.proc_net_dev_keys["rx_bytes"]],
                values[NetworkInterfaces.proc_net_dev_keys["tx_bytes"]],
            )

        # Now create a network interface for each of the entries.
        for device_lines in devices:
            interface = NetworkInterface(device_lines, proc_net_dev_values)

            if (interface.interface not in EXCLUDE_INTERFACES) and (interface.slave is False):
                self[interface.interface] = {
                    "mac_address": interface.mac_address,
                    "inet4_address": interface.inet4_addr,
                    "inet4_prefix": interface.inet4_prefix,
                    "inet6_address": interface.inet6_addr,
                    "type": interface_to_lnet_type(interface.type),
                    "rx_bytes": interface.rx_tx_stats.rx_bytes,
                    "tx_bytes": interface.rx_tx_stats.tx_bytes,
                    "up": interface.up,
                    "slave": interface.slave,
                }

    def name(self, inet4_address):
        result = None

        if inet4_address == "0":
            result = "lo"
        else:
            for name, interface in self.iteritems():
                if interface["inet4_address"] == inet4_address:
                    result = name
                    break

        if result == None:
            raise self.InterfaceNotFound("Unable to find a name for the network address %s" % inet4_address)

        return result


class LNetNid:
    """Created with a single line that is the output of lctl get_param nis, this class will
    parse those lines and end up with a set of properties corresponding to the parsed data

    It also requires a list of the network interfaces on the node so that it can name the nids
    with the interface name (eth0) for example. This name is required as it is more stable than
    the network address.
    """

    def __init__(self, lnet_nis_line, interfaces):
        tokens = lnet_nis_line.split()

        assert len(tokens) == 9, "line: " + lnet_nis_line

        self.nid_address = tokens[0].split("@")[0]  # TODO: Need to convert to an interface
        type_network_no = tokens[0].split("@")[1]

        m = re.match("(\w+?)(\d+)?$", type_network_no)  # Non word, then optional greedy number at end of line.
        self.lnd_type = m.group(1)
        self.lnd_network = m.group(2)
        if not self.lnd_network:
            self.lnd_network = 0

        self.status = tokens[1]
        self.alive = tokens[2]
        self.refs = tokens[3]
        self.peer = tokens[4]
        self.rtr = tokens[5]
        self.max = tokens[6]
        self.tx = tokens[7]
        self.min = tokens[8]

        # I don't like this but we need to key on the name of the port the nid is associated with and
        # I can't see a better way than this to do it, feels clumsy.
        # Nasty, interfaces will not have an entry for lo which is at address '0' in lnet land so just fix
        # that exception up.
        # By default make the name the address, we need something in-case there is no match, and this makes it debuggable.
        self.name = interfaces.name(self.nid_address)


class LinuxNetworkDevicePlugin(DevicePlugin):
    # This need to be instance variables, for reasons that are really difficult to expliain.
    # Generally changes are sent but sometimes we want to poll them. However when we poll we create a new object
    # and so if these are instance variables we don't get the diff back, and so don't see the deletes!
    # last_return is updated in the session_update so a poll sees any deletes but does not stop them being sent in
    # the updates. Ask Chris about this for more info.
    last_return = {}
    cached_results = {}

    def __init__(self, session):
        super(LinuxNetworkDevicePlugin, self).__init__(session)

    def _lnet_devices(self, interfaces):
        """
        :param interfaces: A list of the interfaces on the current node
        :return: Returns a dict of dicts describing the nids on the current node.
        """
        try:
            lines = AgentShell.try_run(["lctl", "get_param", "-n", "nis"]).split("\n")
        except Exception as err:
            daemon_log.warning("get_nids: failed to open: {}".format(err.message))
            return LinuxNetworkDevicePlugin.cached_results

        # Skip header line
        lines = lines[1:]

        # Parse each NID string out into result list
        lnet_nids = []
        for line in lines:
            if not line:
                continue
            try:
                lnet_nids.append(LNetNid(line, interfaces))
            except NetworkInterfaces.InterfaceNotFound as e:
                daemon_log.warning(e)

        result = {}

        for lnet_nid in lnet_nids:
            if lnet_nid.lnd_type not in EXCLUDE_INTERFACES:
                result[lnet_nid.name] = {
                    "nid_address": lnet_nid.nid_address,
                    "lnd_type": lnet_nid.lnd_type,
                    "lnd_network": lnet_nid.lnd_network,
                }

            LinuxNetworkDevicePlugin.cache_results(raw_result=result)

        return result

    @classmethod
    def cache_results(cls, raw_result=None, lnet_configuration=None):
        assert (raw_result == None) or (lnet_configuration == None)

        if lnet_configuration:
            raw_result = {}

            interfaces = NetworkInterfaces()

            for network_interface in lnet_configuration["network_interfaces"]:
                raw_result[interfaces.name(network_interface[0])] = {
                    "nid_address": network_interface[0],
                    "lnd_type": network_interface[1],
                    "lnd_network": network_interface[2],
                }

        cls.cached_results = raw_result

    def _lnet_state(self):
        lnet_up = False
        lnet_loaded = not bool(AgentShell.run(["udevadm", "info", "--path", "/sys/module/lnet"]).rc)

        if lnet_loaded:
            lnet_up = not bool(AgentShell.run(["lnetctl", "net", "show"]).rc)

        return {
            (False, False): "lnet_unloaded",
            (False, True): "lnet_unloaded",
            (True, False): "lnet_down",
            (True, True): "lnet_up",
        }[(lnet_loaded, lnet_up)]

    def start_session(self):
        interfaces = NetworkInterfaces()
        nids = self._lnet_devices(interfaces)

        result = {
            "interfaces": interfaces,
            "lnet": {"state": self._lnet_state(), "nids": nids},
        }

        return result

    def update_session(self):
        this_return = self.start_session()

        # THIS DOESN'T WORK BECAUSE RX/TX change in the network and so the data is sent back everytime. So it does work
        # but the data is always sent to if (true) is really what we have.
        if (this_return != self.last_return) or (self.trigger_plugin_update is True):
            LinuxNetworkDevicePlugin.last_return = this_return
            self.trigger_plugin_update = False
            return self.last_return
        else:
            return
