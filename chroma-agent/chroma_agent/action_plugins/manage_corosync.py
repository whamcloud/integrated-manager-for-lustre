#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


#import socket
#from chroma_agent import shell
#

# FIXME: this appear to be unused
#def verify_corosync():
#    """Verifies the state of corosync"""
#
#    # Is corosync accessible?
#    rc, stdout, stderr = shell.run("crm status", shell=True)
#    if rc != 0:
#        return {'accessible': False,
#                'cluster_member': True,
#                'targets_exist': False
#               }
#
#    # Is this node a member of a cluster?
#    hostname = socket.gethostname()
#    rc, stdout, stderr = shell.run("crm node show %s" % hostname,
#                                       shell=True)
#    if rc != 0 or not "%s: normal" % hostname in stdout:
#        return {'accessible': True,
#                'cluster_member': False,
#                'targets_exist': False
#               }
#
#    # now make sure there are no resources using the Target ocf
#    rc, stdout, stderr = shell.run("crm resource list", shell=True)
#    for line in stdout.split('\n'):
#        if "ocf::chroma:Target" in line:
#            return {'accessible': True,
#                    'cluster_member': True,
#                    'targets_exist': True
#                   }
#
"""
Corosync verification
"""

import socket
import ethtool
from netaddr import IPNetwork, IPAddress
from netaddr.core import AddrFormatError
from time import sleep
from chroma_agent import shell
from chroma_agent.store import AgentStore
from chroma_agent import node_admin
import chroma_agent.fence_agent


from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('chroma_agent', 'templates'))

# The window of time in which we count resource monitor failures
RSRC_FAIL_WINDOW = "20m"
# The number of times in the above window a resource monitor can fail
# before we migrate it
RSRC_FAIL_MIGRATION_COUNT = "3"


class CorosyncRingInterface(object):
    @classmethod
    def ring0(cls):
        # ring0 will always be on the interface used for agent->manager comms
        from urlparse import urlparse
        server_url = AgentStore.get_server_conf()['url']
        manager_address = socket.gethostbyname(urlparse(server_url).hostname)
        rc, out, err = shell.run(['/sbin/ip', 'route', 'get', manager_address])
        manager_dev = out.split()[2]
        return cls(manager_dev)

    @classmethod
    def ring1(cls, device, ipaddr, netmask, mcast_port):
        # ring1 is auto-configured on the first-available unconfigured
        # ethernet interface that has physical link
        ring0 = cls.ring0()
        if ring0.ipv4_prefixlen < 9:
            raise RuntimeError("Network on %s cannot be bigger than /9 (%s)" %
                               (ring0.name, ring0.ipv4_prefixlen))
        ring1_address = IPAddress(ipaddr)
        prefixlen = IPNetwork("0.0.0.0/%s" % netmask).prefixlen

        iface = cls(device, ringnumber = 1)
        iface.set_address("%s/%s" % (ring1_address, prefixlen))
        iface.mcastport = int(mcast_port)

        return iface

    def __init__(self, name, ringnumber=0):
        self.name = name
        self.refresh()
        self.ringnumber = ringnumber
        self.ring1_peers = []
        self.mcastport = 0

    def __getattr__(self, attr):
        if hasattr(self._info, attr):
            return getattr(self._info, attr)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, attr))

    def set_address(self, address):
        shell.try_run(['/sbin/ifconfig', self.name, address, 'up'])
        self.refresh()
        node_admin.write_ifcfg(self.device, self.mac_address,
                               self.ipv4_address, self.ipv4_netmask)

    def refresh(self):
        self._info = ethtool.get_interfaces_info(self.name)[0]
        try:
            self._network = IPNetwork("%s/%s" % (self._info.ipv4_address,
                                                 self._info.ipv4_netmask))
        except AddrFormatError:
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


class AutoDetectedInterface(CorosyncRingInterface):
    @classmethod
    def all_interfaces(cls):
        # Not sure how robust this will be; need to test with real gear.
        # In theory, should do the job to exclude IPoIB and lo interfaces.
        hwaddr_blacklist = ['00:00:00:00:00:00', '80:00:00:48:fe:80']
        eth_interfaces = []
        for device in ethtool.get_devices():
            if ethtool.get_hwaddr(device) not in hwaddr_blacklist:
                eth_interfaces.append(cls(device))

        return eth_interfaces

    @classmethod
    def detect_ring1(cls, ring0):
        # find a good place for the ring1 network
        ring1_subnet = cls.find_subnet(ring0.ipv4_network,
                                       ring0.ipv4_prefixlen)
        ring1_address = str(IPAddress((int(IPAddress(ring0.ipv4_hostmask)) &
                                       int(IPAddress(ring0.ipv4_address))) |
                                      int(ring1_subnet.ip)))

        all_interfaces = AutoDetectedInterface.all_interfaces()
        # Find potential ring1 interface auto-configure candidates
        if ring1_address not in [i.ipv4_address for i in all_interfaces]:
            for iface in all_interfaces:
                if not iface.ipv4_address and iface.has_link:
                    iface.set_address("%s/%s" % (ring1_address,
                                                 ring0.ipv4_prefixlen))
                    break

        for iface in all_interfaces:
            if iface.ipv4_address != ring1_address:
                continue

            iface.ringnumber = 1

            # Now we need to agree on a mcastport for these peers.
            # First we have to find a free one since we can't spend
            # the time searching after deciding one is not being used
            # already because that delays the discovery of us by our peer
            iface.mcastport = iface.find_unused_port(ring0)

            # Now see if one is being used on ring1
            # Note: we randomize the timeout to reduce races
            # XXX: a better algorithm here might be to just have all
            #      nodes figure out the available ports and choose one
            #      at random and then everyone announces their choice
            #      with lowest (or highest) choice wins and eveyrone
            #      uses that
            from random import randint
            iface.discover_existing_mcastport(timeout = randint(5, 20))

            return iface

    # given a network, find another as big in RFC-1918 space
    # passes for these tests:
    # 192.168.1.0/24
    # 10.0.1.0/24
    # 10.128.0.0/9
    # 10.127.255.254/9
    # 10.255.255.255/32
    @classmethod
    def find_subnet(self, network, prefixlen):
        _network = IPNetwork("%s/%s" % (network, prefixlen))
        if _network >= IPNetwork("10.0.0.0/8") and \
           _network < IPAddress("10.255.255.255"):
            if _network >= IPNetwork("10.128.0.0/9"):
                shadow_network = IPNetwork("10.0.0.0/%s" % prefixlen)
            else:
                shadow_network = IPNetwork("10.128.0.0/%s" % prefixlen)
        else:
            shadow_network = IPNetwork("10.0.0.0/%s" % prefixlen)
        return shadow_network

    def find_unused_port(self, iface, timeout = 10):
        import time
        from random import choice

        interface = iface.name
        dest_addr = iface.mcastaddr
        ports = range(1, 65535, 2)

        self.subscribe_multicast(iface)
        cap = self.start_cap(interface, timeout, "host %s and udp" % dest_addr)

        def recv_packets(header, data):
            tgt_port = self.get_dport_from_packet(data)

            try:
                ports.remove(tgt_port)
            except ValueError:
                # already removed
                pass

        start = time.time()
        while time.time() - start < timeout:
            try:
                cap.dispatch(-1, recv_packets)
            except Exception, e:
                raise RuntimeError("Error reading from the network: %s" % str(e))
        return choice(ports)

    def discover_existing_mcastport(self, timeout = 10):
        import time

        interface = self.name
        dest_addr = self.mcastaddr

        self.subscribe_multicast(self)
        cap = self.start_cap(interface, timeout, "host %s and udp" % dest_addr)

        self.num_recvd = 0

        def recv_packets(header, data):
            self.mcastport = self.get_dport_from_packet(data)
            self.num_recvd = self.num_recvd + 1

        start = time.time()
        while self.num_recvd < 1 and time.time() - start < timeout:
            try:
                cap.dispatch(1, recv_packets)
            except Exception, e:
                raise RuntimeError("Error reading from the network: %s" %
                                   str(e))

    def subscribe_multicast(self, iface):
        # subscribe to the mcast addr
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 52122))
        mreq = socket.inet_aton(iface.mcastaddr) + \
               socket.inet_aton(iface.ipv4_address)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def start_cap(self, interface, timeout, filter):
        import pcapy
        try:
            cap = pcapy.open_live(interface, 64, True, timeout * 1000)
            cap.setfilter(filter)
        except Exception, e:
            raise RuntimeError("Error doing open_live() / setfilter()" %
                               str(e))
        return cap

    def get_dport_from_packet(self, data):
        import impacket
        import impacket.ImpactDecoder
        decoder = impacket.ImpactDecoder.EthDecoder()
        try:
            packet = decoder.decode(data)
            return packet.child().child().get_uh_dport()
        except Exception, e:
            raise RuntimeError("Error decoding network packet: %s" %
                               str(e))

    @property
    def has_link(self):
        import array
        import struct
        import fcntl
        SIOCETHTOOL = 0x8946
        ETHTOOL_GLINK = 0x0000000a
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ecmd = array.array('B', struct.pack('2I', ETHTOOL_GLINK, 0))
        ifreq = struct.pack('16sP', self.name, ecmd.buffer_info()[0])
        fcntl.ioctl(sock.fileno(), SIOCETHTOOL, ifreq)
        sock.close()
        return bool(struct.unpack('4xI', ecmd.tostring())[0])


def _render_config_file(path, config):
    import os
    import errno
    import shutil
    from tempfile import mkstemp
    tmpf, tmpname = mkstemp()
    os.write(tmpf, config)
    try:
        shutil.move(path, "%s.old" % path)
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise e
    os.close(tmpf)
    # no easier way to get a filename from a fd?!?
    shutil.copy(tmpname, path)


def configure_corosync(ring1_iface = None, ring1_ipaddr = None, ring1_netmask = None, mcast_port = None):
    conf_template = env.get_template('corosync.conf')
    ring0 = CorosyncRingInterface.ring0()
    if ring1_iface:
        ring1 = CorosyncRingInterface.ring1(ring1_iface, ring1_ipaddr,
                                            ring1_netmask, mcast_port)
    else:
        ring1 = AutoDetectedInterface.detect_ring1(ring0)

    if not ring1:
        raise RuntimeError("Failed to detect ring1 interface")

    interfaces = [ring0, ring1]
    interfaces[0].mcastport = interfaces[1].mcastport

    _render_config_file("/etc/corosync/corosync.conf",
                        conf_template.render(interfaces=interfaces))

    # install a firewall rule for this port
    shell.try_run(['/usr/sbin/lokkit', '-n', '-p', '%s:udp' %
                   interfaces[0].mcastport])
    # XXX using -n above and installing the rule manually here is a
    #     dirty hack due to restarting the firewall interrupting our
    #     comms with the manager
    #     can we re-initiate somehow?
    shell.try_run(['/sbin/iptables', '-I', 'INPUT', '-m', 'state', '--state',
                   'new', '-p', 'udp', '--dport',
                   str(interfaces[0].mcastport), '-j', 'ACCEPT'])
    # XXX - need to fix AgentStore needs an "add key" functionality
    url = AgentStore.get_server_conf()['url']
    AgentStore.set_server_conf({'url': url, 'mcastport': interfaces[0].mcastport})

    # pacemaker MUST be stopped before doing this or this will spin
    # forever
    unconfigure_pacemaker()
    shell.try_run(['/sbin/service', 'corosync', 'restart'])
    shell.try_run(['/sbin/chkconfig', 'corosync', 'on'])


def get_cluster_size():
    # you'd think there'd be a way to query the value of a prooperty
    # such as "expected-quorum-votes" but there does not seem to be, so
    # just count nodes instead (of waiting for the end of the crm configure
    # show output to parse the properties list)
    rc, stdout, stderr = shell.run(["crm_node", "-l"])

    if not stdout:
        return 0

    n = 0
    for line in stdout.rstrip().split('\n'):
        node_id, name, status = line.split(" ")
        if status == "member" or status == "lost":
            n = n + 1

    return n


def configure_pacemaker():
    shell.try_run(['/sbin/service', 'pacemaker', 'restart'])
    # need to wait for the CIB to be ready
    timeout = 120
    while timeout > 0:
        rc, stdout, stderr = shell.run(['crm_mon', '-1'])
        for line in stdout.split('\n'):
            if line.startswith("Current DC:"):
                if line[line.find(":") + 2:] != "NONE":
                    timeout = -1
                    break
        sleep(1)
        timeout = timeout - 1

    if timeout == 0:
        raise RuntimeError("Failed to start pacemaker")

    shell.try_run(['/sbin/chkconfig', 'pacemaker', 'on'])

    # ignoring quorum should only be done on clusters of 2
    if get_cluster_size() > 2:
        no_quorum_policy = "stop"
    else:
        no_quorum_policy = "ignore"

    _unconfigure_fencing()
    # this could race with other cluster members to make sure
    # any errors are only due to it already existing
    try:
        shell.try_run(["pcs", "resource", "create",
                       "st-fencing", "stonith:fence_chroma"])
    except:
        rc, stdout, stderr = shell.run(["pcs", "resource", "show",
                                        "st-fencing"])
        if rc == 0:
            # no need to do the rest if another member is already doing it
            return
        else:
            raise

    shell.try_run(["pcs", "property", "set",
                   "no-quorum-policy=%s" % no_quorum_policy])
    shell.try_run(["pcs", "property", "set",
                   "symmetric-cluster=true"])
    shell.try_run(["pcs", "property", "set",
                   "cluster-infrastructure=openais"])
    shell.try_run(["pcs", "property", "set", "stonith-enabled=true"])
    shell.try_run(["pcs", "resource", "rsc", "defaults",
                   "resource-stickiness=1000"])
    shell.try_run(["pcs", "resource", "rsc", "defaults",
                   "failure-timeout=%s" % RSRC_FAIL_WINDOW])
    shell.try_run(["pcs", "resource", "rsc", "defaults",
                   "migration-threshold=%s" % RSRC_FAIL_MIGRATION_COUNT])


def configure_fencing(fence_agent, ipaddr = None, login = None,
                      password = None, plug = None):

    def set_attribute(name, value):
        print "setting %s = %s" % (name, value)
        shell.try_run(["crm_attribute", "--node", node,
                       "--name", name, "-update", value])

    node = socket.gethostname()

    # first clear existing fence_attributes
    for attribute in ["agent", "login", "password", "ipaddr", "plug"]:
        rc, stdout, stderr = shell.run(["crm_attribute", "--node",
                                        node,
                                        "--name", "fence_%s" % attribute,
                                        "--delete"])
    if rc != 0 and rc != 234:
        raise RuntimeError("Failed to delete node attribute")

    set_attribute("fence_agent", "fence_%s" % fence_agent)
    if login:
        set_attribute("fence_login", login)
    if password:
        set_attribute("fence_password", password)
    if ipaddr:
        set_attribute("fence_ipaddr", ipaddr)
    if plug:
        set_attribute("fence_plug", plug)

    agent = getattr(chroma_agent.fence_agent, fence_agent)
    agent(node).initialize()


def unconfigure_corosync():
    from os import remove
    import errno

    shell.try_run(['service', 'corosync', 'stop'])
    shell.try_run(['/sbin/chkconfig', 'corosync', 'off'])
    try:
        remove("/etc/corosync/corosync.conf")
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise RuntimeError("Failed to remove corosync.conf")
    except:
        raise RuntimeError("Failed to remove corosync.conf")

    mcastport = AgentStore.get_server_conf()['mcastport']
    # it really bites that lokkit has no "delete" functionality
    shell.try_run(['/sbin/iptables', '-D', 'INPUT', '-m', 'state', '--state',
                   'new', '-p', 'udp', '--dport', str(mcastport), '-j',
                   'ACCEPT'])
    import os
    from tempfile import mkstemp
    import shutil
    tmp = mkstemp(dir = "/etc/sysconfig")
    with os.fdopen(tmp[0], "w") as tmpf:
        for line in open("/etc/sysconfig/iptables").readlines():
            if line.rstrip() != "-A INPUT -m state --state NEW -m udp -p udp --dport %s -j ACCEPT" % mcastport:
                tmpf.write(line)
        tmpf.flush()
    shutil.move(tmp[1], "/etc/sysconfig/iptables")


def pacemaker_running():
    rc, stdout, stderr = shell.run(["crm_mon", "-1"])
    if rc != 0:
        return False

    return True


def unconfigure_pacemaker():
    # only unconfigure if we are the only node in the cluster
    # but first, see if pacemaker is up to answer this
    if not pacemaker_running():
        # and just skip doing this if it's not
        return 0

    if get_cluster_size() < 2:
        # last node, nuke the CIB
        cibadmin(["-f", "-E"])

    shell.try_run(['/sbin/service', 'pacemaker', 'stop'])

    shell.try_run(['/sbin/chkconfig', 'pacemaker', 'off'])


def _unconfigure_fencing():
    shell.run(["pcs", "resource", "delete", "st-fencing"])


def unconfigure_fencing():
    # only unconfigure if we are the only node in the cluster
    # but first, see if pacemaker is up to answer this
    if not pacemaker_running():
        # and just skip doing this if it's not
        return 0

    if get_cluster_size() > 1:
        return 0

    _unconfigure_fencing()


def delete_node(nodename):
    rc, stdout, stderr = shell.run(['crm_node', '-l'])
    node_id = None
    for line in stdout.split('\n'):
        node_id, name, status = line.split(" ")
        if name == nodename:
            break
    shell.try_run(['crm_node', '--force', '-R', node_id])
    cibadmin(["--delete", "--obj_type", "nodes", "-X",
              "<node uname=\"%s\"/>" % nodename])
    cibadmin(["--delete", "--obj_type", "nodes", "--crm_xml",
              "<node_state uname=\"%s\"/>" % nodename])


def cibadmin(command_args):
    from time import sleep
    from chroma_agent import shell

    # try at most, 100 times
    n = 100
    rc = 10

    while (rc == 10 or rc == 107) and n > 0:
        rc, stdout, stderr = shell.run(['cibadmin'] + command_args)
        if rc == 0:
            break
        sleep(1)
        n -= 1

    if rc != 0:
        raise RuntimeError("Error (%s) running 'cibadmin %s': '%s' '%s'" %
                           (rc, " ".join(command_args), stdout, stderr))

    return rc, stdout, stderr

ACTIONS = [configure_corosync, unconfigure_corosync,
           configure_pacemaker, unconfigure_pacemaker,
           configure_fencing, unconfigure_fencing,
           delete_node]
