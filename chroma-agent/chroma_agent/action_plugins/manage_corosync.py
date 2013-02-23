#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


"""
Corosync verification
"""

from netaddr import IPNetwork
from time import sleep

from chroma_agent import shell
from chroma_agent.lib.system import add_firewall_rule, del_firewall_rule

# The window of time in which we count resource monitor failures
RSRC_FAIL_WINDOW = "20m"
# The number of times in the above window a resource monitor can fail
# before we migrate it
RSRC_FAIL_MIGRATION_COUNT = "3"


def configure_corosync(ring1_iface = None, ring1_ipaddr = None, ring1_netmask = None, mcast_port = None):
    from chroma_agent.lib.corosync import CorosyncRingInterface, get_ring0, generate_ring1_network, detect_ring1, render_config, write_config_to_file

    ring0 = get_ring0()
    if not ring1_ipaddr and not ring1_netmask:
        ring1_ipaddr, ring1_prefix = generate_ring1_network(ring0)
    elif ring1_netmask:
        ring1_prefix = str(IPNetwork("0.0.0.0/%s" % ring1_netmask).prefixlen)

    if ring1_iface and ring1_ipaddr and ring1_prefix and mcast_port:
        ring1 = CorosyncRingInterface(name = ring1_iface,
                                      ringnumber = 1,
                                      mcastport = int(mcast_port))
        ring1.set_address(ring1_ipaddr, ring1_prefix)
    else:
        ring1 = detect_ring1(ring0, ring1_ipaddr, ring1_prefix)

    if not ring1:
        raise RuntimeError("Failed to detect ring1 interface")

    interfaces = [ring0, ring1]
    interfaces[0].mcastport = interfaces[1].mcastport

    config = render_config(interfaces)
    write_config_to_file("/etc/corosync/corosync.conf", config)

    add_firewall_rule(interfaces[0].mcastport, "udp", "corosync")

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
    n = 0
    for line in stdout.rstrip().split('\n'):
        node_id, name, status = line.split(" ")
        if status == "member" or status == "lost":
            n = n + 1

    return n


def configure_pacemaker():
    # Corosync needs to be running for pacemaker -- if it's not, make
    # an attempt to get it going.
    if shell.run(['/sbin/service', 'corosync', 'status'])[0]:
        shell.try_run(['/sbin/service', 'corosync', 'restart'])
        shell.try_run(['/sbin/service', 'corosync', 'status'])

    shell.try_run(['/sbin/service', 'pacemaker', 'restart'])
    # need to wait for the CIB to be ready
    timeout = 120
    while timeout > 0:
        rc, stdout, stderr = shell.run(['crm', 'status'])
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
        shell.try_run(["crm", "-F", "configure", "primitive",
                       "st-fencing", "stonith:fence_chroma"])
    except:
        rc, stdout, stderr = shell.run(["crm", "resource", "show",
                                        "st-fencing"])
        if rc == 0:
            # no need to do the rest if another member is already doing it
            return
        else:
            raise

    shell.try_run(["crm", "configure", "property",
                   "no-quorum-policy=\"%s\"" % no_quorum_policy])
    shell.try_run(["crm", "configure", "property",
                   "symmetric-cluster=\"true\""])
    shell.try_run(["crm", "configure", "property",
                   "cluster-infrastructure=\"openais\""])
    shell.try_run(["crm", "configure", "property", "stonith-enabled=\"true\""])
    shell.try_run(["crm", "configure", "rsc_defaults",
                   "resource-stickiness=1000"])
    shell.try_run(["crm", "configure", "rsc_defaults",
                   "failure-timeout=%s" % RSRC_FAIL_WINDOW])
    shell.try_run(["crm", "configure", "rsc_defaults",
                   "migration-threshold=%s" % RSRC_FAIL_MIGRATION_COUNT])


def configure_fencing(agents):
    import socket
    from chroma_agent.lib.pacemaker import PacemakerConfig

    pc = PacemakerConfig()
    node = pc.get_node(socket.gethostname())

    node.clear_fence_attributes()

    if isinstance(agents, basestring):
        # For CLI debugging
        import json
        agents = json.loads(agents)

    for idx, agent in enumerate(agents):
        node.set_fence_attributes(idx, agent)


def set_node_standby(node):
    from chroma_agent.lib.pacemaker import PacemakerConfig

    pc = PacemakerConfig()
    node = pc.get_node(node)
    node.enable_standby()


def set_node_online(node):
    from chroma_agent.lib.pacemaker import PacemakerConfig

    pc = PacemakerConfig()
    node = pc.get_node(node)
    node.disable_standby()


def unconfigure_corosync():
    from os import remove
    import errno
    import re

    shell.try_run(['service', 'corosync', 'stop'])
    shell.try_run(['/sbin/chkconfig', 'corosync', 'off'])
    mcastport = None

    with open("/etc/corosync/corosync.conf") as f:
        for line in f.readlines():
            match = re.match("\s*mcastport:\s*(\d+)", line)
            if match:
                mcastport = match.group(1)
                break
    if mcastport is None:
        raise RuntimeError("Failed to find mcastport in corosync.conf")

    try:
        remove("/etc/corosync/corosync.conf")
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise RuntimeError("Failed to remove corosync.conf")
    except:
        raise RuntimeError("Failed to remove corosync.conf")

    del_firewall_rule(mcastport, "udp", "corosync")


def unconfigure_pacemaker():
    # only unconfigure if we are the only node in the cluster
    # but first, see if pacemaker is up to answer this
    rc, stdout, stderr = shell.run(["crm", "status"])
    if rc != 0:
        # and just skip doing this if it's not
        return 0
    if get_cluster_size() < 2:
        # last node, nuke the CIB
        cibadmin(["-f", "-E"])

    shell.try_run(['/sbin/service', 'pacemaker', 'stop'])

    shell.try_run(['/sbin/chkconfig', 'pacemaker', 'off'])


def _unconfigure_fencing():
    shell.run(["crm", "resource", "stop", "st-fencing"])
    shell.run(["crm", "configure", "delete", "st-fencing"])


def unconfigure_fencing():
    # only unconfigure if we are the only node in the cluster
    # but first, see if pacemaker is up to answer this
    rc, stdout, stderr = shell.run(["crm", "status"])
    if rc != 0:
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

    while rc == 10 and n > 0:
        rc, stdout, stderr = shell.run(['cibadmin'] + command_args)
        if rc == 0:
            break
        sleep(1)
        n -= 1

    if rc != 0:
        raise RuntimeError("Error (%s) running 'cibadmin %s': '%s' '%s'" %
                           (rc, " ".join(command_args), stdout, stderr))

    return rc, stdout, stderr


def host_corosync_config():
    """
    If desired, automatic corosync configuration can be bypassed by creating
    an /etc/chroma.cfg file containing parameters for the configure_corosync
    function.

    Example 1: Allow automatic assignment of ring1 network parameters
    [corosync]
    mcast_port = 4400
    ring1_iface = eth1

    Example 2: Specify all parameters to completely bypass automatic config
    [corosync]
    mcast_port = 4400
    ring1_iface = eth1
    ring1_ipaddr = 10.42.42.10
    ring1_netmask = 255.255.0.0
    """
    from ConfigParser import SafeConfigParser

    parser = SafeConfigParser()
    parser.add_section('corosync')
    parser.read("/etc/chroma.cfg")
    return dict(parser.items('corosync'))


ACTIONS = [configure_corosync, unconfigure_corosync,
           configure_pacemaker, unconfigure_pacemaker,
           configure_fencing, unconfigure_fencing,
           set_node_standby, set_node_online,
           host_corosync_config, delete_node]
