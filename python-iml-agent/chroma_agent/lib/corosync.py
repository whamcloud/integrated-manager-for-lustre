# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import os
import time
import re
import socket

from jinja2 import Environment, PackageLoader
from netaddr import IPNetwork, IPAddress
from netaddr.core import AddrFormatError
from urlparse import urljoin

from chroma_agent import config
from chroma_agent.lib import node_admin
from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log
from iml_common.lib.firewall_control import FirewallControl
from iml_common.lib.service_control import ServiceControl
from chroma_agent.lib import networking
from chroma_agent.lib.talker_thread import TalkerThread
from scapy.all import sniff, UDP, IP
from toolz import groupby

env = Environment(loader=PackageLoader("chroma_agent", "templates"))

firewall_control = FirewallControl.create(logger=console_log)

# Used to make noise on ring1 to enable corosync detection.
talker_thread = None

operstate = "/sys/class/net/{}/operstate"


def filter_unclean_nodes(nodes):
    """Given a list of nodes,
    returns the clean ones.
    """
    x = groupby(lambda x: x.get("unclean"), nodes)

    return x.get("false", [])


def get_cluster_node_name():
    try:
        return AgentShell.try_run(["crm_node", "-n"]).strip()
    except Exception as e:
        console_log.info("Could not get cluster node name {}. Falling back to socket.getfqdn()".format(e))

        return socket.getfqdn()


class RingDetectionError(Exception):
    pass


def get_all_interfaces():
    import ethtool

    # Not sure how robust this will be; need to test with real gear.
    # In theory, should do the job to exclude IPoIB and lo interfaces.
    hwaddr_blacklist = ["00:00:00:00:00:00", "80:00:00:48:fe:80"]
    eth_interfaces = []
    for device in ethtool.get_devices():
        if ethtool.get_hwaddr(device) not in hwaddr_blacklist:
            eth_interfaces.append(CorosyncRingInterface(device))

    return eth_interfaces


def generate_ring1_network(ring0):
    # find a good place for the ring1 network
    subnet = find_subnet(ring0.ipv4_network, ring0.ipv4_prefixlen)
    address = str(
        IPAddress((int(IPAddress(ring0.ipv4_hostmask)) & int(IPAddress(ring0.ipv4_address))) | int(subnet.ip))
    )
    console_log.info("Chose %s/%d for ring1 address" % (address, subnet.prefixlen))
    return address, str(subnet.prefixlen)


def get_shared_ring():
    # The shared ring will always be on the interface used for agent->manager comms
    from urlparse import urlparse

    server_url = urljoin(os.environ["IML_MANAGER_URL"], "agent")
    manager_address = socket.gethostbyname(urlparse(server_url).hostname)
    out = AgentShell.try_run(["/sbin/ip", "route", "get", manager_address])
    match = re.search(r"dev\s+([^\s]+)", out)
    if match:
        manager_dev = match.groups()[0]
    else:
        raise RuntimeError("Unable to find ring0 dev in {}".format(out))

    console_log.info("Chose %s for corosync ring0" % manager_dev)
    shared_ring = CorosyncRingInterface(manager_dev, ringnumber=1)

    if shared_ring.ipv4_prefixlen < 9:
        raise RuntimeError("{} subnet is too large (/{})".format(shared_ring.name, shared_ring.ipv4_prefixlen))

    return shared_ring


def detect_ring1(ring0, ring1_address, ring1_prefix):
    all_interfaces = get_all_interfaces()

    if len(all_interfaces) < 2:
        raise RingDetectionError(
            "Corosync requires at least 2 network interaces, "
            "one of which my be unconfigured and dedicated to HA monitoring."
            "Only %s interfaces found" % len(all_interfaces)
        )

    ring1_candidates = []

    # If the specified ring1 address is not already configured, get
    # a list of ring1 candidates from the set of interfaces which
    # are unconfigured and have positive link status.
    if ring1_address not in [i.ipv4_address for i in all_interfaces]:
        for iface in all_interfaces:
            if not iface.ipv4_address and iface.has_link and not iface.is_slave:
                ring1_candidates.append(iface)

    # If we've found exactly 1 unconfigured interface with link, we'll
    # configure it as our ring1 interface.
    if len(ring1_candidates) == 1:
        iface = ring1_candidates[0]
        console_log.info("Chose %s for corosync ring1" % iface.name)
        iface.set_address(ring1_address, ring1_prefix)
    elif len(ring1_candidates) > 1:
        raise RingDetectionError(
            "Unable to autodetect ring1: found %d unconfigured interfaces with link" % len(ring1_candidates)
        )

    # Now, go back and look through the list of all interfaces again for
    # our ring1 address. We do it this way in order to handle the situation
    # where the ring1 interface was already configured and we just need to
    # find a corosync multicast port.
    for iface in all_interfaces:
        if iface.ipv4_address != ring1_address:
            continue

        # This toggles things like multicast group, etc.
        iface.ringnumber = 0

        # Now we need to agree on a mcastport for these peers.
        # First we have to find a free one since we can't spend
        # the time searching after deciding one is not being used
        # already because that delays the discovery of us by our peer
        iface.mcastport = find_unused_port(ring0)
        console_log.info("Proposing %d for multicast port" % iface.mcastport)

        # Now see if one is being used on ring1
        discover_existing_mcastport(iface, timeout=30)
        console_log.info("Decided on %d for multicast port" % iface.mcastport)

        return iface

    raise RingDetectionError("Failed to detect ring1 interface")


def find_subnet(network, prefixlen):
    """
    given a network, find another as big in RFC-1918 space
    passes for these tests:
    192.168.1.0/24
    10.0.1.0/24
    10.128.0.0/9
    10.127.255.254/9
    10.255.255.255/32
    """
    _network = IPNetwork("%s/%s" % (network, prefixlen))
    if IPNetwork("10.0.0.0/8") <= _network < IPAddress("10.255.255.255"):
        if _network >= IPNetwork("10.128.0.0/9"):
            shadow_network = IPNetwork("10.0.0.0/%s" % prefixlen)
        else:
            shadow_network = IPNetwork("10.128.0.0/%s" % prefixlen)
    else:
        shadow_network = IPNetwork("10.0.0.0/%s" % prefixlen)
    return shadow_network


def find_unused_port(ring0, timeout=10, batch_count=10000):
    from random import choice

    dest_addr = ring0.mcastaddr
    port_min = 32767
    port_max = 65535
    ports = range(port_min, port_max, 2)
    portrange_str = "%s-%s" % (port_min, port_max)

    firewall_control.add_rule(0, "tcp", "find unused port", persist=False, address=ring0.mcastaddr)

    try:
        console_log.info("Sniffing packets on {}({}) within range: {}".format(ring0.name, dest_addr, portrange_str))

        dports = sniff(
            iface=ring0.name,
            lfilter=lambda x: x.haslayer(UDP)
            and isinstance(x[UDP].dport, (int, long))
            and x[UDP].dport >= port_min
            and x[UDP].dport <= port_max
            and x[IP].dst == dest_addr,
            timeout=timeout,
        )

        console_log.info("Finished after %d seconds, sniffed: %d" % (timeout, len(dports)))

        for dport in dports:
            try:
                ports.remove(dport)
            except ValueError:
                # already removed
                pass

    finally:
        firewall_control.remove_rule(0, "tcp", "find unused port", persist=False, address=ring0.mcastaddr)

    return choice(ports)


def _corosync_listener(service, action):
    if service == "corosync" and action == ServiceControl.ServiceState.SERVICESTARTED:
        console_log.debug("Corosync has been started by this node")
        _stop_talker_thread()


def _start_talker_thread(interface):
    global talker_thread

    if talker_thread is None:
        console_log.debug("Starting talker thread")
        talker_thread = TalkerThread(interface, console_log)
        talker_thread.start()
        ServiceControl.register_listener("corosync", _corosync_listener)


def _stop_talker_thread():
    global talker_thread

    if talker_thread is not None:
        console_log.debug("Stopping talker thread")
        talker_thread.stop()
        talker_thread = None
        ServiceControl.unregister_listener("corosync", _corosync_listener)


def discover_existing_mcastport(ring1, timeout=10):
    console_log.info("Sniffing for packets on {}({})".format(ring1.name, ring1.mcastaddr))

    # Stop the talker thread if it is running.
    _stop_talker_thread()

    # Start the talker thread
    _start_talker_thread(ring1)

    ring1_original_mcast_port = ring1.mcastport

    try:
        dports = sniff(
            lfilter=lambda x: x.haslayer(UDP)
            and isinstance(x[UDP].dport, (int, long))
            and x[IP].dst == ring1.mcastaddr
            and x[IP].src != ring1.ipv4_address,
            iface=ring1.name,
            count=1,
            timeout=timeout,
        )

        dports = map(lambda x: x[UDP].dport, dports)

        console_log.debug("Finished after %d seconds, sniffed: %d" % (timeout, len(dports)))

        if len(dports):
            ring1.mcastport = dports.pop()
            console_log.debug("Sniffed multicast traffic on %d" % ring1.mcastport)
    finally:
        # If we heard someone else talking (ring1_original_mcast_post != ring1.mcast_post)
        # then stop the talker thread, otherwise we should continue to fill the dead air until we start corosync.
        if ring1_original_mcast_port != ring1.mcastport:
            _stop_talker_thread()


def render_config(interfaces):
    conf_template = env.get_template("corosync.conf")
    return conf_template.render(interfaces=interfaces)


def write_config_to_file(path, config):
    import os
    import errno
    import shutil
    from tempfile import mkstemp

    tmpf, tmpname = mkstemp()
    os.write(tmpf, config)
    try:
        shutil.move(path, "%s.old" % path)
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise e
    os.close(tmpf)
    # no easier way to get a filename from a fd?!?
    shutil.copy(tmpname, path)


class CorosyncRingInterface(object):
    """
    Provides a wrapper around an ethtool device with extra functionality
    specific to corosync configuration.
    """

    IFF_LIST = [
        "IFF_ALLMULTI",
        "IFF_AUTOMEDIA",
        "IFF_BROADCAST",
        "IFF_DEBUG",
        "IFF_DYNAMIC",
        "IFF_LOOPBACK",
        "IFF_MASTER",
        "IFF_MULTICAST",
        "IFF_NOARP",
        "IFF_NOTRAILERS",
        "IFF_POINTOPOINT",
        "IFF_PORTSEL",
        "IFF_PROMISC",
        "IFF_RUNNING",
        "IFF_SLAVE",
        "IFF_UP",
    ]

    def __init__(self, name, ringnumber=0, mcastport=0):
        # ethtool does NOT like unicode
        self.name = str(name)
        self.refresh()
        self.ringnumber = ringnumber
        self.mcastport = mcastport

    def __getattr__(self, attr):
        flag = "IFF_%s" % attr[3:].upper()
        if attr.startswith("is_") and flag in self.IFF_LIST:
            import ethtool

            return ethtool.get_flags(self.name) & getattr(ethtool, flag) > 0

        if hasattr(self._info, attr):
            return getattr(self._info, attr)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, attr))

    def set_address(self, ipv4_address, prefix):
        ifaddr = "%s/%s" % (ipv4_address, prefix)

        if not ipv4_address or not prefix:
            console_log.info("Set {} called with invalid parameters: {}".format(self.name, ifaddr))
            return

        console_log.info("Set %s (%s) up" % (self.name, ifaddr))

        if self.ipv4_address != ipv4_address:
            node_admin.unmanage_network(self.device, self.mac_address)

            AgentShell.try_run(["/sbin/ip", "link", "set", "dev", self.name, "up"])
            AgentShell.try_run(["/sbin/ip", "addr", "add", ifaddr, "dev", self.name])

            # The link address change is asynchronous, so we need to wait for the
            # address to stick of we have a race condition.
            timeout = 30
            while self.ipv4_address != ipv4_address and timeout != 0:
                self.refresh()
                time.sleep(1)
                timeout -= 1

            if self.ipv4_address != ipv4_address:
                raise RuntimeError("Unable to set the address %s for interface %s" % (self.ipv4_address, self.name))

            node_admin.write_ifcfg(self.device, self.mac_address, self.ipv4_address, self.ipv4_netmask)
        else:
            console_log.info("Nothing to do as %s already has address %s" % (self.name, ifaddr))

    def refresh(self):
        import ethtool

        self._info = ethtool.get_interfaces_info(self.name)[0]
        try:
            self._network = IPNetwork("%s/%s" % (self._info.ipv4_address, self._info.ipv4_netmask))
        except (UnboundLocalError, AddrFormatError):
            pass

    @property
    def ipv4_hostmask(self):
        return str(self._network.hostmask)

    @property
    def ipv4_prefixlen(self):
        return self._info.ipv4_netmask

    @property
    def ipv4_address(self):
        return self._info.ipv4_address

    @property
    def ipv4_netmask(self):
        # etherinfo.ipv4_netmask returns a cidr prefix (e.g. 24), but
        # things like ifcfg want a subnet mask.
        return str(IPNetwork("0.0.0.0/%s" % self._info.ipv4_netmask).netmask)

    @property
    def mcastaddr(self):
        return "226.94.%s.1" % self.ringnumber

    @property
    def ipv4_network(self):
        try:
            return str(self._network.network)
        except AttributeError:
            return None

    @property
    def bindnetaddr(self):
        return self.ipv4_network

    @property
    def has_link(self):
        old_link_state_up = self.is_up

        # HYD-2003: Some NICs require the interface to be in an UP state
        # before link detection will work.
        time_left = 0

        if not self.is_up:
            AgentShell.try_run(["/sbin/ip", "link", "set", "dev", self.name, "up"])
            time_left = 10

        def _get_device_state(name):
            try:
                filepath = operstate.format(name)
                if os.path.exists(filepath):
                    with open(filepath, "r") as f:
                        return f.read().strip()
                else:
                    return "unknown"
            except IOError:
                print("Could not read state of ethernet device {}".format(name))
                return "unknown"

        def _has_link():
            return _get_device_state(self.name) == "up"

        try:
            while time_left:
                # Poll for link status on newly-up interfaces
                if _has_link():
                    return True
                else:
                    time.sleep(1)
                    time_left -= 1

            return _has_link()
        except IOError:
            # If the ioctl fails, then for the purposes of this test, the
            # interface is not usable. HYD-2679
            return False
        finally:
            if not old_link_state_up:
                AgentShell.try_run(["/sbin/ip", "link", "set", "dev", self.name, "down"])


def corosync_running():
    return ServiceControl.create("corosync").running
