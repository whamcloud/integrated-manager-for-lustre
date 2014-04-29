#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

from chroma_agent import shell
from chroma_agent.lib.system import add_firewall_rule, del_firewall_rule
from chroma_agent.lib.pacemaker import cibadmin, PacemakerConfig
from chroma_agent.log import daemon_log

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
    # you'd think there'd be a way to query the value of a property
    # such as "expected-quorum-votes" but there does not seem to be, so
    # just count nodes instead
    rc, stdout, stderr = shell.run(["crm_node", "-l"])

    if not stdout:
        return 0

    n = 0
    for line in stdout.rstrip().split('\n'):
        node_id, name, status = line.split(" ")
        if status == "member" or status == "lost":
            n = n + 1

    return n


def enable_pacemaker():
    shell.try_run(['/sbin/chkconfig', '--add', 'pacemaker'])
    shell.try_run(['/sbin/chkconfig', 'pacemaker', 'on'])


def configure_pacemaker():
    # Corosync needs to be running for pacemaker -- if it's not, make
    # an attempt to get it going.
    if shell.run(['/sbin/service', 'corosync', 'status'])[0]:
        shell.try_run(['/sbin/service', 'corosync', 'restart'])
        shell.try_run(['/sbin/service', 'corosync', 'status'])

    enable_pacemaker()
    shell.try_run(['/sbin/service', 'pacemaker', 'restart'])

    pc = PacemakerConfig()

    if not pc.is_dc:
        daemon_log.info("Skipping (global) pacemaker configuration because I am not the DC")
        return

    # ignoring quorum should only be done on clusters of 2
    if len(pc.nodes) > 2:
        no_quorum_policy = "stop"
    else:
        no_quorum_policy = "ignore"

    _unconfigure_fencing()
    # this could race with other cluster members to make sure
    # any errors are only due to it already existing
    try:
        cibadmin(["--create", "--obj_type", "resources", "-X",
                  "<primitive class=\"stonith\" id=\"st-fencing\" type=\"fence_chroma\"/>"])
    except:
        rc, stdout, stderr = shell.run(['crm_resource', '--locate',
                                        '--resource', "st-fencing"])
        if rc == 0:
            # no need to do the rest if another member is already doing it
            return
        else:
            raise

    cibadmin(["--modify", "--allow-create", "-o", "crm_config", "-X",
              '''<cluster_property_set id="cib-bootstrap-options">
<nvpair id="cib-bootstrap-options-no-quorum-policy" name="no-quorum-policy" value="%s"/>
<nvpair id="cib-bootstrap-options-symmetric-cluster" name="symmetric-cluster" value="true"/>
<nvpair id="cib-bootstrap-options-cluster-infrastructure" name="cluster-infrastructure" value="openais"/>
<nvpair id="cib-bootstrap-options-stonith-enabled" name="stonith-enabled" value="true"/>
</cluster_property_set>''' % no_quorum_policy])

    def set_rsc_default(name, value):
        shell.try_run(["crm_attribute", "--type", "rsc_defaults",
                       "--attr-name", name, "--attr-value", value])
    set_rsc_default("resource-stickiness", "1000")
    set_rsc_default("failure-timeout", RSRC_FAIL_WINDOW)
    set_rsc_default("migration-threshold", RSRC_FAIL_MIGRATION_COUNT)


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
    cibadmin(["--delete", "--obj_type", "resources", "-X",
              "<primitive class=\"stonith\" id=\"st-fencing\" type=\"fence_chroma\"/>"])


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
    from ConfigParser import SafeConfigParser, Error as ConfigError
    config_file = "/etc/chroma.cfg"

    parser = SafeConfigParser()
    parser.add_section('corosync')
    try:
        parser.read(config_file)
        return dict(parser.items('corosync'))
    except ConfigError as e:
        daemon_log.error("Failed to parse %s: %s" % (config_file, e))
        return {}


ACTIONS = [configure_corosync, unconfigure_corosync,
           enable_pacemaker, configure_pacemaker, unconfigure_pacemaker,
           configure_fencing, unconfigure_fencing,
           set_node_standby, set_node_online,
           host_corosync_config, delete_node]
